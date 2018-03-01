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
#define ENCRYPTED_MESSAGE_LEN 48 //for withdrawal
#define MAX_BILLS 128
#define BILL_LEN 16
#define UUID_LEN 36
#define PROV_MSG "P"
#define WITH_OK "K"
#define WITH_BAD "BAD"
#define RECV_OK "K"
#define EMPTY "EMPTY"
#define EMPTY_BILL "*****EMPTY*****"

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

// global EEPROM read variables
static const uint8 MONEY[MAX_BILLS][BILL_LEN] = {EMPTY_BILL};
static const uint8 UUID[UUID_LEN + 1] = {'b', 'l', 'a', 'n', 'k', ' ', 
										'u', 'u', 'i', 'd', '!', 0x00 };
static const uint8 BILLS_LEFT[1] = {0x00};

// new consts below - see protocol_details.txt
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

uint8_t request[100]; // when HSM receives message
uint8_t response[100]; // when HSM sends out a message
uint8 message_type;
uint32_t current_nonce[32];
uint32_t secret_key; // this will be stored/accessed in the eeprom

// reset interrupt on button press
CY_ISR(Reset_ISR)
{
	pushMessage((uint8*)"In interrupt\n", strlen("In interrupt\n"));
	SW1_ClearInterrupt();
	CySoftwareReset();
}


// provisions HSM (should only ever be called once)

//TODO: ALL OF THIS IS BROKEN, I'LL REWORK IT
void provision()
{
	int i;
	uint8 message[64], numbills;

	for(i = 0; i < 128; i++) {
		PIGGY_BANK_Write((uint8*)EMPTY_BILL, MONEY[i], BILL_LEN);
	}

    // synchronize with atm
	syncConnection(SYNC_PROV);

	memset(message, 0u, 64);
	strcpy((char*)message, PROV_MSG);
	pushMessage(message, (uint8)strlen(PROV_MSG));

    // Set UUID
	pullMessage(message, 1);
	PIGGY_BANK_Write(message, UUID, strlen((char*)message) + 1);
	pushMessage((uint8*)RECV_OK, strlen(RECV_OK));

    // Get numbills
	pullMessage(message, 1);
	numbills = message[0];
	PIGGY_BANK_Write(&numbills, BILLS_LEFT, 1u);
	pushMessage((uint8*)RECV_OK, strlen(RECV_OK));

    // Load bills
	for (i = 0; i < numbills; i++) {
		pullMessage(message, 1);
		PIGGY_BANK_Write(message, MONEY[i], BILL_LEN);
		pushMessage((uint8*)RECV_OK, strlen(RECV_OK));
	}

    // Generate shared secret with server

    // todo: do this
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
    CyGlobalIntEnable; /* Enable global interrupts. */

    // start reset button
	Reset_isr_StartEx(Reset_ISR);

    /* Declare vairables here */

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
    static const uint8 PROVISIONED[1] = {0x00}; // write variable
    volatile const uint8* ptr = PROVISIONED;    // read variable
    
    
    /* Place your initialization/startup code here (e.g. MyInst_Start()) */
    
    PIGGY_BANK_Start();
    DB_UART_Start();
    
    // provision security module on first boot
    if(*ptr == 0x00)
    {
    	provision();

        // Mark as provisioned
    	i = 0x01;
    	PIGGY_BANK_Write(&i, PROVISIONED,1u);
    }
    
    // Go into infinite loop
    while (1) {
        /* Place your application code here. */

        // synchronize with bank
    	syncConnection(SYNC_NORM);

        // receive message (expecting nonce request)
    	pullMessage(message, (uint8)1);
        message_type = message[0]; // read off first byte of request

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
	        	// generate nonce
	        	hydro_random_buf(&current_nonce, 32);
	        	// send nonce
	        	response[0] = NONCE_RESPONSE;
	        	for (i = 0; i < NONCE_LEN; i++) {
	        		response[i + 1] = current_nonce[i]; 
	        	}
	        	pushMessage(response,NONCE_LEN);
	        	break;

        	case (int)WITHDRAWAL_REQUEST:
	        	// verify signed request
    	        pullMessage(message, ENCRYPTED_MESSAGE_LEN);
	        	uint8_t message [MESSAGE_LEN];
	        	uint8_t* ciphertext = &request;
	        	if (hydro_secretbox_decrypt(message, ciphertext, CIPHERTEXT_LEN,
	        		(uint64_t) 0, "WITHDRAW", secret_key)!=0) {
	        		// message forged!
                    pushMessage(&REJECTED,1);
	        		break;
	        	}		
		        else {
		        	// verify nonce
		        	for (j = 1; j < 33; j++) {
		        		if (message[j] != current_nonce[j - 1]) {
		        			flag = 1;
		        		}
		        	}
                    if (message[0]!=WITHDRAWAL_REQUEST){
                        pushMessage(&REJECTED,1);//Not a withdrawal request
                    }
		        	if (flag == 0) { // if nonce check passed
			        	uint8 numbills = message[1 + 32]; // (WITHDRAW (1 byte)| nonce (32 bytes)| amount)
			        	ptr = BILLS_LEFT;
			        	if (*ptr < numbills) {
                            pushMessage(&REJECTED,1);//wrong nonce
			        		break;
			        	} 
			        	else {
                            pushMessage(&RETURN_WITHDRAWAL, 1);
                            pushMessage(&ACCEPTED, 1);
                            pushMessage(&numbills, 1);

			        		bills_left = *ptr - numbills;
			        		PIGGY_BANK_Write(&bills_left, BILLS_LEFT, 0x01);
			        	}

			        	for (i = 0; i < numbills; i++) {
			        		dispenseBill();
			        	}
	        	        
                        hydro_random_buf(&current_nonce, 32);// resets the nonce to prevent replays
		        		break;
		        	}
	        	}
    	}
	}
}

// Old Code:
        /*
        // send UUID
        ptr = UUID;
        pushMessage((uint8*)ptr, strlen((char*)ptr));
        
        // get returned UUID
        pullMessage(message);
        
        // compare UUID with stored UUID
        if (strcmp((char*)message, (char*)UUID)) {
            pushMessage((uint8*)WITH_BAD, strlen(WITH_BAD));
        } else {
            pushMessage((uint8*)WITH_OK, strlen(WITH_OK));
            
            // get number of bills
            pullMessage(message);
            numbills = message[0];
            
            ptr = BILLS_LEFT;
            if (*ptr < numbills) {
                pushMessage((uint8*)WITH_BAD, strlen(WITH_BAD));
                continue;
            } else {
                pushMessage((uint8*)WITH_OK, strlen(WITH_OK));
                bills_left = *ptr - numbills;
                PIGGY_BANK_Write(&bills_left, BILLS_LEFT, 0x01);
            }
            
            for (i = 0; i < numbills; i++) {
                dispenseBill();
            }
        }
        */

/* [] END OF FILE */
