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
#include "common.h"

//This is needed for the default communication between the BANK and DISPLAY over the USB-UART
#include "usbserialprotocol.h"
#include "SW1.h"

// Crypto library
#include "hydrogen.h"


// Global EEPROM variables
static const uint8 MONEY[MAX_BILLS][BILL_LEN]   = {EMPTY_BILL};
static const uint8 UUID[UUID_LEN]               = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static const uint8 ENC_KEY[HSM_KEY_LEN]         = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static const uint8 BILLS_LEFT[1]                = {0x00};
static const uint8 PROVISIONED[1]               = {0x00};
static const uint8 CURRENT_NONCE[NONCE_LEN]     = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};




// Reset interrupt on button press
CY_ISR(Reset_ISR)
{
	pushMessage((uint8*)"In interrupt\n", strlen("In interrupt\n"));
	SW1_ClearInterrupt();
	CySoftwareReset();
}


// Provisions HSM (should only ever be called once)
void provision()
{
    uint8 message_type;
    
    uint8 hsm_key_buf[HSM_KEY_LEN];
    uint8 rand_key_buf[RAND_KEY_LEN];
    uint8 uuid_buf[UUID_LEN];
    
    uint8 num_bills;
    uint8 bill[BILL_LEN];
    
    //set the bill array to be all empty
	for(int i = 0; i < MAX_BILLS; i++) {
		PIGGY_BANK_Write((uint8*)EMPTY_BILL, MONEY[i], BILL_LEN);
	}
    
    // Synchronize with ATM
	syncConnection(SYNC_PROV);
    
    pullMessage(&message_type, 1);
        
    // check if provision message
    if (message_type != REQUEST_PROVISION) {
	    pushMessage(&REJECTED, 1);
        return;
    } 
    

        
    //get the hsm enc key, randomness key, and uuid
    pullMessage(hsm_key_buf, HSM_KEY_LEN);    
	pushMessage(&ACCEPTED, 1);
    pullMessage(rand_key_buf, RAND_KEY_LEN);
    pushMessage(&ACCEPTED, 1);
    pullMessage(uuid_buf, UUID_LEN);
    
    
    //write them to eeprom
    PIGGY_BANK_Write(hsm_key_buf, ENC_KEY, HSM_KEY_LEN);
    PIGGY_BANK_Write(rand_key_buf, rand_key, RAND_KEY_LEN);
	PIGGY_BANK_Write(uuid_buf, UUID, UUID_LEN);
    
    pushMessage(&INITIATE_BILLS_REQUEST, 1);
    
    pullMessage(&message_type, 1);
    if (message_type != BILLS_REQUEST) {
        pushMessage(&REJECTED, 1);
        return;
    }
    
    // Get number of bills
    pullMessage(&num_bills, 1);
    
	PIGGY_BANK_Write(&num_bills, BILLS_LEFT, 1u);

    // Load bills
	for (int i = num_bills - 1; i >= 0; i--) {
		pullMessage(bill, BILL_LEN);
		PIGGY_BANK_Write(bill, MONEY[i], BILL_LEN);
        pushMessage(&BILL_RECEIVED, 1);
	}
    pushMessage(&ACCEPTED, 1);
}

void dispenseBill()
{
    uint8 bills_left;
    uint8 bill[BILL_LEN];
    
    eeprom_copy(&bills_left, (const volatile uint8 *)BILLS_LEFT, 1);
    if (bills_left <= 0)
        return;
    
    eeprom_copy(bill, (const volatile uint8 *)MONEY[bills_left - 1], BILL_LEN);
	pushMessage(bill, BILL_LEN);

	PIGGY_BANK_Write((uint8*)EMPTY_BILL, MONEY[bills_left - 1], BILL_LEN);
    bills_left -= 1;
    PIGGY_BANK_Write(&bills_left, BILLS_LEFT, 1);
}

void generateNonce(uint8 *nonce)
{
    hydro_random_buf(nonce, NONCE_LEN);
    PIGGY_BANK_Write(nonce, CURRENT_NONCE, NONCE_LEN);
}

int main(void)
{
	// Enable global interrupts
    CyGlobalIntEnable; 

    // Start reset button
	Reset_isr_StartEx(Reset_ISR);

    /* Place your initialization/startup code here (e.g. MyInst_Start()) */
    PIGGY_BANK_Start();
    DB_UART_Start();
    
    // Provision security module on first boot
    if (*(volatile const uint8 *)PROVISIONED == 0x00)
    {
        //initial connection sync
        syncConnection(SYNC_PROV);
    	provision();

        // Mark as provisioned
    	PIGGY_BANK_Write((uint8[]){0x01}, PROVISIONED, 1u);
    }
    else 
    {
        //initial connection sync
        syncConnection(SYNC_NORM);
    }
    
    // Go into infinite loop
    while (1) {
        uint8 message_type;
        
        // Synchronize with atm
    	syncConnection(SYNC_NORM);

    	pullMessage(&message_type, 1);

        switch(message_type)
        {
        	case UUID_REQUEST:
            {
                uint8 uuid[UUID_LEN];
                eeprom_copy(uuid, (volatile const uint8 *)UUID, UUID_LEN);
                
                pushMessage(&UUID_RESPONSE, 1);
	        	pushMessage(uuid, UUID_LEN);
	        	break;
            }
        	case NONCE_REQUEST:
            {
                uint8 nonce[NONCE_LEN];
                
                generateNonce(nonce);
                
                pushMessage(&NONCE_RESPONSE, 1);
                pushMessage(nonce, NONCE_LEN);
	        	break;
            }
            case REQUEST_BALANCE:
            {
                uint8 ciphertext[CHECK_BALANCE_CIPHERTEXT_LEN];
	        	uint8 plaintext[1 + NONCE_LEN + BALANCE_LEN];
                uint8 key[HSM_KEY_LEN];
                uint8 curr_nonce[NONCE_LEN];
                
                eeprom_copy(key, (const volatile uint8 *)ENC_KEY, HSM_KEY_LEN);
                eeprom_copy(curr_nonce, (const volatile uint8 *)CURRENT_NONCE, NONCE_LEN);

                pullMessage(ciphertext, CHECK_BALANCE_CIPHERTEXT_LEN);

			    // decrypt message, fail if authentication is wrong
	        	if (hydro_secretbox_decrypt(plaintext, ciphertext, CHECK_BALANCE_CIPHERTEXT_LEN, 0, CONTEXT, key)) 
                {
                    pushMessage(&REJECTED,1);
	        		break;
	        	}	
                
                //ptext format: OPCODE | HSM_NONCE | BALANCE
                
                // Send message if request is not a balance request
                if (plaintext[0] != REQUEST_BALANCE)
                {
                    pushMessage(&REJECTED,1);
                    break;
                }
		        else {
                    //check that the nonce matches
                    if (memcmp(plaintext + 1, curr_nonce, NONCE_LEN))
                    {
                        pushMessage(&REJECTED,1);
                        break;
                    }
                    
					// Resets the nonce to prevent replays
                    generateNonce(curr_nonce);
                    
                    /* Handle actual balance check */
                    
                    // Push the balance to the atm
                    pushMessage(&RETURN_BALANCE, 1);
                    pushMessage(&plaintext[1 + NONCE_LEN], BALANCE_LEN);
		        	break;
                }
            }
        	case WITHDRAWAL_REQUEST:
            {
                uint8 ciphertext[WITHDRAW_CIPHERTEXT_LEN];
	        	uint8 plaintext[1 + NONCE_LEN + 1]; //opcode + nonce + 1 byte for num bills
                uint8 key[HSM_KEY_LEN];
                uint8 curr_nonce[NONCE_LEN];
                uint8 withdraw_amount;
                uint8 bills_left;
                
                eeprom_copy(key, (const volatile uint8 *)ENC_KEY, HSM_KEY_LEN);
                eeprom_copy(curr_nonce, (const volatile uint8 *)CURRENT_NONCE, NONCE_LEN);
                eeprom_copy(&bills_left, (const volatile uint8 *)BILLS_LEFT, 1);
                
                pullMessage(ciphertext, WITHDRAW_CIPHERTEXT_LEN);

			    // decrypt message, fail if authentication is wrong
	        	if (hydro_secretbox_decrypt(plaintext, ciphertext, WITHDRAW_CIPHERTEXT_LEN, 0, CONTEXT, key)) 
                {
                    pushMessage(&REJECTED,1);
	        		break;
	        	}	
                
                // Send message if request is not a balance request
                if (plaintext[0] != WITHDRAWAL_REQUEST)
                {
                    pushMessage(&REJECTED,1);
                    break;
                }
                
                //check that the nonce matches
                if (memcmp(plaintext + 1, curr_nonce, NONCE_LEN))
                {
                    pushMessage(&REJECTED,1);
                    break;
                }
                    
		        // Resets the nonce to prevent replays
                generateNonce(curr_nonce);
                    
                /* Handle actual withdrawal */
                    
                withdraw_amount = plaintext[1 + NONCE_LEN];
                if (bills_left < withdraw_amount) 
                {
                    pushMessage(&REJECTED,1); // dont have the funds to handle this withdrawal
		            break;
                }
                
                pushMessage(&RETURN_WITHDRAWAL, 1);
                pushMessage(&withdraw_amount, 1);
                
                for (int i = 0; i < withdraw_amount; i++) {
		        	dispenseBill();
		        }
                
	        	break;
            }
    	}
	}
}   
