/* ========================================
 *
 * Copyright YOUR COMPANY, THE YEAR
 * All Rights Reserved
 * UNPUBLISHED, LICENSED SOFTWARE.
 *
 * CONFIDENTIAL AND PROPRIETARY INFORMATION
 * WHICH IS THE PROPERTY OF your company.
 *
 * ========================================
*/
#include "project.h"
#include <stdlib.h>
#include <string.h>
//This is needed for the default communication between the BANK and DISPLAY over the USB-UART
#include "usbserialprotocol.h"
#include "SW1.h"
// Crypto library
#include "hydrogen.h"

// SECURITY MODULE
#define NONCE_LEN 32
#define ENCRYPTED_MESSAGE_LEN 48 // For withdrawal
#define MAX_BILLS 128
#define BILL_LEN 16
#define UUID_LEN 36
#define PROV_MSG "P"
#define WITH_OK "K"
#define WITH_BAD "BAD"
#define RECV_OK "K"
#define EMPTY "EMPTY"
#define EMPTY_BILL "*****EMPTY*****"

#define INITIATE_PROVISION 0x25
#define REQUEST_PROVISION 0x26
#define INITIATE_BILLS_REQUEST 0x27
#define BILLS_REQUEST 0x28
#define BILL_RECEIVED 0x29

/* 
 * How to read from EEPROM (persistent memory):
 * 
 * // read variable:
 * static const uint8 EEPROM_BUF_VAR[len] = { val1, val2, ... };
 * // write variable:
 * volatile const uint8 *ptr = EEPROM_BUF_VAR;
 * 
 * uint8 val1 = *ptr;
 * uint8 buf[4] = { 0x01, 0x02, 0x03, 0x04 };
 * USER_INFO_Write(message, EEPROM_BUF_VAR, 4u); 
 */

// Global EEPROM read variables
static const uint8 MONEY[MAX_BILLS][BILL_LEN] = {EMPTY_BILL};
static const uint8 UUID[UUID_LEN + 1] = {'b', 'l', 'a', 'n', 'k', ' ', 
										'u', 'u', 'i', 'd', '!', 0x00 };
static const uint8 ENC_KEY[32] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                  0x00, 0x00, 0x00, 0x00};
static const uint8 RAND_KEY[32] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                  0x00, 0x00, 0x00, 0x00};
static const uint8 BILLS_LEFT[1] = {0x00};

// New consts below - see protocol_details.txt
static const int CIPHERTEXT_LEN = 256;
static const int MESSAGE_LEN = 256; 
static const uint8 UUID_REQUEST = 0x06; 
static const uint8 UUID_RESPONSE = 0x07; 
static const uint8 NONCE_REQUEST = 0x04;
static const uint8 NONCE_RESPONSE = 0x05;
static const uint8 WITHDRAWAL_REQUEST = 0x08; 
static const uint8 RETURN_WITHDRAWAL = 0x09;
static const uint8 REJECTED = 0x21; 
static const uint8 ACCEPTED = 0x20; 

uint8_t request[100]; // When HSM receives message
uint8_t response[100]; // When HSM sends out a message
uint8 message_type;
uint32_t current_nonce[32];
uint32_t secret_key; // This will be stored/accessed in the eeprom

// Reset interrupt on button press
CY_ISR(Reset_ISR)
{
	pushMessage((uint8*)"In interrupt\n", strlen("In interrupt\n"));
	SW1_ClearInterrupt();
	CySoftwareReset();
}


// Provisions HSM (should only ever be called once)

//TODO: FIX THIS
void provision()
{
	int i;
	uint8 message[101], numbills;

	for(i = 0; i < 128; i++) {
		PIGGY_BANK_Write((uint8*)EMPTY_BILL, MONEY[i], BILL_LEN);
	}

    // Synchronize with ATM
	syncConnection(0);

	// Push provisioning message
	pushMessage((uint8*)INITIATE_PROVISION, (uint8)1);

    pullMessage((uint8*)message, (uint8)101);
    
    if (message[0] != REQUEST_PROVISION) {
        // Throw Error
        pushMessage(&REJECTED, (uint8)1);
    }
    // message:
    // code (1 byte) | enc key (32 bytes) | rand key (32 byte) | UUID (36 bytes) 
    
    // Set enc key
    PIGGY_BANK_Write(&message[1], ENC_KEY, (uint8)32);
    
    // Set rand key
    PIGGY_BANK_Write(&message[33], RAND_KEY, (uint8)32);
    
    // Set UUID
	PIGGY_BANK_Write(&message[65], UUID, (uint8)36);
    
    pushMessage((uint8*)INITIATE_BILLS_REQUEST, (uint8)1);
    
    pullMessage((uint8*)message, (uint8)2);
    
    if (message[0] != BILLS_REQUEST) {
        // Throw Error
        pushMessage(&REJECTED, (uint8)1);
    }
    
    // Get number of bills
    numbills = message[1];
	PIGGY_BANK_Write(&numbills, BILLS_LEFT, 1u);

    // Load bills
	for (i = 0; i < numbills; i++) {
		pullMessage(message, 1);
		PIGGY_BANK_Write(message, MONEY[i], BILL_LEN);
        pushMessage((uint8*)BILL_RECEIVED, (uint8)1);
	}
}


void dispenseBill()
{
	static uint8 stackloc = 0;
	uint8 message[16];
	volatile const uint8* ptr; 

	ptr = MONEY[stackloc];

	memset(message, 0u, 16);
	memcpy(message, (void*)ptr, BILL_LEN);
	
	pushMessage(message, BILL_LEN);

	PIGGY_BANK_Write((uint8*)EMPTY_BILL, MONEY[stackloc], 16);
	stackloc = (stackloc + 1) % 128;
}


int main(void)
{
	// Enable global interrupts
    	CyGlobalIntEnable; 

    	// Start reset button
	Reset_isr_StartEx(Reset_ISR);

    	// Declare variables here
	uint8 numbills, i, bills_left;
	uint8 message[64];

    /*
     * Note:
     *  To write to EEPROM, write to static const uint8 []
     *  To read from EEPROM, read from volatile const uint8 * 
     *      set to write variable
     *
     * PSoC EEPROM is very finnicky if this format is not followed
     */

    static const uint8 PROVISIONED[1] = {0x00}; // Write variable
    volatile const uint8* ptr = PROVISIONED;    // Read variable
    
    
    /* Place your initialization/startup code here (e.g. MyInst_Start()) */
    
    PIGGY_BANK_Start();
    DB_UART_Start();
    
    // Provision security module on first boot
    if(*ptr == 0x00)
    {
    	provision();

        // Mark as provisioned
    	i = 0x01;
    	PIGGY_BANK_Write(&i, PROVISIONED,1u);
    }
    
    // Go into infinite loop
    while (1) {
        /* Application code */

        // Synchronize with bank
    	syncConnection(1);

        // Receive message (expecting nonce request)
    	pullMessage(message, (uint8)1);
		// Read off first byte of request
        message_type = message[0]; 

        int i, j;
        int flag = 0;

        switch(message_type)
        {
        	case (int)UUID_REQUEST:
	        	response[0] = UUID_RESPONSE;

	        	for (i = 0; i < UUID_LEN; i++) {
	        		response[i + 1] = UUID[i]; 
	        	}

	        	pushMessage(response,UUID_LEN);
	        	break;

        	case (int)NONCE_REQUEST:
	        	// Generate nonce
	        	hydro_random_buf(&current_nonce, 32);
	        	// Send nonce
	        	response[0] = NONCE_RESPONSE;

	        	for (i = 0; i < NONCE_LEN; i++) {
	        		response[i + 1] = current_nonce[i]; 
	        	}

	        	pushMessage(response,NONCE_LEN);
	        	break;

        	case (int)WITHDRAWAL_REQUEST:
	        	// Verify signed request
    	        pullMessage(message, ENCRYPTED_MESSAGE_LEN);
	        	uint8_t plaintext[MESSAGE_LEN];

			// Check if message is forged
	        	if (hydro_secretbox_decrypt(plaintext, message, CIPHERTEXT_LEN,
	        		(uint64_t) 0, "WITHDRAW", ENC_KEY)!=0) {
                    		pushMessage(&REJECTED,1);
	        		break;
	        	}		

		        else {
		        	// Verify nonce
		        	for (j = 1; j < 33; j++) {
		        		if (plaintext[j] != current_nonce[j - 1]) {
		        			flag = 1;
		        		}
		        	}

				// Send message if request is not a withdrawal request
                    		if (plaintext[0]!=WITHDRAWAL_REQUEST){
                        		pushMessage(&REJECTED,1);
                    		}

				// If nonce checked passed 
		        	if (flag == 0) { 
			        	uint8 numbills = plaintext[1 + 32]; // (WITHDRAW (1 byte)| nonce (32 bytes)| amount)
			        	ptr = BILLS_LEFT;

			        	if (*ptr < numbills) {
                            			pushMessage(&REJECTED,1); // Wrong nonce
			        		break;
			        	} 

			        	else {
						// Send accepted withdrawal messagae
                            			pushMessage(&RETURN_WITHDRAWAL, 1);
                            			pushMessage(&ACCEPTED, 1);
                            			pushMessage(&numbills, 1);

			        		bills_left = *ptr - numbills;
			        		PIGGY_BANK_Write(&bills_left, BILLS_LEFT, 0x01);
			        	}

			        	for (i = 0; i < numbills; i++) {
			        		dispenseBill();
			        	}
	        	        
					// Resets the nonce to prevent replays
                        		hydro_random_buf(&current_nonce, 32);
		        		break;
		        	}
	        	}
    	}
	}
}
