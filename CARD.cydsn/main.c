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
#include "usbserialprotocol.h"
#include "SW1.h"
#include "Reset_isr.h"
#include <hydrogen.h>

#define PIN_LEN 8
#define UUID_LEN 36
#define R_LEN 32
#define NONCE_LEN 32
#define SIG_LEN 32
#define PK_LEN 32


#define PINCHG_SUC "SUCCESS"
#define PROV_MSG "P"
#define RECV_OK "K"
#define PIN_OK "OK"
#define PIN_BAD "BAD"

#define REQUEST_NAME            0x00
#define RETURN_NAME             0x01
#define REQUEST_CARD_SIGNATURE  0x02
#define RETURN_CARD_SIGNATURE   0x03
#define REQUEST_NEW_PK          0x0C
#define RETURN_NEW_PK           0x0D


//CARD

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
static const uint8 R[R_LEN] = {};
static const uint8 UUID[UUID_LEN] = {0x37, 0x33, 0x36, 0x35, 0x36, 0x33, 0x37, 0x35, 0x37, 0x32, 0x36, 0x39, 0x37, 0x34, 0x37, 0x39}; //security

// more variables
uint8_t request[100]; // when HSM receives message
uint8_t response[100]; // when HSM sends out a message
uint8_t message_type;
uint8_t r[32];
uint32_t secret_key;

// libhydrogen variables
hydro_sign_keypair key_pair;

uint8_t signature[32];
hydro_sign_state st;

// reset interrupt on button press
CY_ISR(Reset_ISR)
{
    pushMessage((uint8*)"In interrupt\n", strlen("In interrupt\n"));
    SW1_ClearInterrupt();
    CySoftwareReset();
}

// provisions card (should only ever be called once)
void provision()
{
    uint8 message[64];
    
    // synchronize with bank
    syncConnection(SYNC_PROV);
 
    pushMessage((uint8*)PROV_MSG, (uint8)strlen(PROV_MSG));
    
    // get r (random)
    pullMessage(message);
    USER_INFO_Write(message, R, R_LEN);
    pushMessage((uint8*)RECV_OK, strlen(RECV_OK));         

    // set account number
    pullMessage(message);
    USER_INFO_Write(message, UUID, UUID_LEN);
    pushMessage((uint8*)RECV_OK, strlen(RECV_OK));
}


int main(void)
{
    // enable global interrupts -- DO NOT DELETE
    CyGlobalIntEnable;
    
    // start reset button
    Reset_isr_StartEx(Reset_ISR);
    
    /* Declare vairables here */
    uint8 i;
    uint8 message[128];
    
    // local EEPROM read variable
    static const uint8 PROVISIONED[1] = {0x00};
    
    // EEPROM write variable
    volatile const uint8 *ptr;
    
    /* Place your initialization/startup code here (e.g. MyInst_Start()) */
    USER_INFO_Start();
    USB_UART_Start();
    
    pushMessage("test", 5);
    
    // Provision card if on first boot
    ptr = PROVISIONED;
    if (*ptr == 0x00) {
        provision();
        
        // Mark as provisioned
        i = 0x01;
        USER_INFO_Write(&i,PROVISIONED, 1u);
    }
    
    // Go into infinite loop
    while (1) {
        //get message type
        syncConnection(SYNC_NORM);
        pullMessage2(message, (uint8)1);
	    message_type = request[0];
	    
        int j;
	    switch(message_type)
	    {
	        case REQUEST_NAME:
            {
		        response[0] = RETURN_NAME;
		        for (j = 0; j < UUID_LEN; j++)
		        {
		            response[j+1] = UUID[j];
		        }
		        pushMessage(response, UUID_LEN);
		        break;
            }
	        case REQUEST_CARD_SIGNATURE:
            {
		        int nonce[32];
		        for (j = 0; j < NONCE_LEN; j++)
		        {
		            nonce[j] = request[j+1];
		        }

		        int pin[8];
		        for (j = 0; j < PIN_LEN; j++)
		        {
		            pin[j] = request[NONCE_LEN + 1 + j];
		        }

        		// Get the seed value by encrypting the PIN with R
        		uint8_t ciphertext[32];
        		hydro_secretbox_encrypt(ciphertext, pin, PIN_LEN, 0, "__seed__", R);

        		// Get the public and the secret key
        		hydro_sign_keygen_deterministic(&key_pair, ciphertext);

        		// generate signature
        		hydro_sign_create(signature, nonce, NONCE_LEN, "__sign__", key_pair.sk);

        		response[0] = RETURN_CARD_SIGNATURE;
        		for (j = 0; j < SIG_LEN; j++)
                        {
                           response[j+1] = signature[j];
                        }
        		pushMessage(response, SIG_LEN);
        		break;
            }

    	    case REQUEST_NEW_PK:
            {
        		int pin[8];
                        for (j = 0; j < PIN_LEN; j++)
                        {
                            pin[j] = request[1 + j];
                        }
        		
        		// Get the seed value by encrypting the PIN with R
                        uint8_t ciphertext[32];
                        hydro_secretbox_encrypt(ciphertext, pin, PIN_LEN, 0, "__seed__", R);

                        // Get the public and the secret key
                        hydro_sign_keygen_deterministic(&key_pair, ciphertext);

        		response[0] = RETURN_NEW_PK;
        		for (j = 0; j < hydro_sign_PUBLICKEYBYTES; j++)
                        {
                           response[j+1] = key_pair.pk[j];
                        }
                        pushMessage(response, PK_LEN);
        		break;
            }

    	    default:
    	        break;
        }
	}	

        
	/*
        // syncronize communication with bank
        syncConnection(SYNC_NORM);
        
        // receive pin number from ATM
        pullMessage(message);
        
	
        if (strncmp((char*)message, (char*)PIN, PIN_LEN)) {
            pushMessage((uint8*)PIN_BAD, strlen(PIN_BAD));
        } else {
            pushMessage((uint8*)PIN_OK, strlen(PIN_OK));
            
            // get command
            pullMessage(message);
            pushMessage((uint8*)RECV_OK, strlen(RECV_OK));
            
            // change PIN or broadcast UUID
            if(message[0] == CHANGE_PIN)
            {
                pullMessage(message);
                USER_INFO_Write(message, PIN, PIN_LEN);
                
                pushMessage((uint8*)PINCHG_SUC, strlen(PINCHG_SUC));
            } else {
                pushMessage(UUID, UUID_LEN);   
            }
        }
	*/
}

/* [] END OF FILE */
