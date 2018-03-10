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
#include "common.h"


// global EEPROM read variables
static const uint8 R[R_LEN]                 = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static const uint8 UUID[UUID_LEN]           = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static const uint8 PROVISIONED[1]           = {0x00};

// reset interrupt on button get r (random)press
CY_ISR(Reset_ISR)
{
    //pushMessage((uint8*)"In interrupt\n", strlen("In interrupt\n"));
    SW1_ClearInterrupt();
    CySoftwareReset();
}

// provisions card (should only ever be called once)
void provision()
{      
    // synchronize with atm
    syncConnection(SYNC_PROV);
    
    uint8 message_type;
    pullMessage(&message_type, 1);
    
    // check if provision message
    if (message_type != REQUEST_PROVISION) {
	    pushMessage(&REJECTED, 1);
        return;
    } 
    
    uint8 r_buf[R_LEN];
    uint8 rand_key_buf[RAND_KEY_LEN];
    uint8 uuid_buf[UUID_LEN];
    
    // get r + randomness key + account number
    pullMessage(r_buf, R_LEN);
    pullMessage(rand_key_buf, RAND_KEY_LEN);
    pullMessage(uuid_buf, UUID_LEN);

    // write them to eeprom
	USER_INFO_Write(r_buf, R, R_LEN);
	USER_INFO_Write(rand_key_buf, rand_key, RAND_KEY_LEN);
	USER_INFO_Write(uuid_buf, UUID, UUID_LEN);

	pushMessage(&ACCEPTED, 1);
}

// Compute H_{r}(pin), use it as a seed for deriving a keypair, and output the keys to kp
void generate_keys(uint8 pin[], hydro_sign_keypair *kp) 
{
    hydro_hash_state state;                
    uint8 seed[SEED_LEN];
    
    // Read R from eeprom
    uint8 r_buf[R_LEN];
    eeprom_copy(r_buf, (const volatile uint8*)R, R_LEN);
    
    hydro_hash_init(&state, CONTEXT, r_buf);
    hydro_hash_update(&state, pin, PIN_LEN);
    hydro_hash_final(&state, seed, SEED_LEN);
                
    // Get the public and the secret key from the seed
    hydro_sign_keygen_deterministic(kp, seed);
}

int main(void)
{
    // enable global interrupts -- DO NOT DELETE
    CyGlobalIntEnable;
    
    // start reset button
    Reset_isr_StartEx(Reset_ISR);
    
    /* Place your initialization/startup code here (e.g. MyInst_Start()) */
    USER_INFO_Start();
    USB_UART_Start();
    
    // Provision card if on first boot
    if (*(volatile const uint8 *)PROVISIONED == 0x00) 
    {
        //handle initial connection sync
        syncConnection(SYNC_PROV);
        provision();
        
        // Mark as provisioned
        USER_INFO_Write((uint8[]){0x01}, PROVISIONED, 1u);
    }
    else 
    {
        //Handle initial connection sync
        syncConnection(SYNC_NORM);
    }
    
    // Go into infinite loop
    while (1) {
        uint8 message_type;
                
        syncConnection(SYNC_NORM);
        
        //get message type
        pullMessage(&message_type, 1);
	    
	    switch(message_type)
	    {
	        case REQUEST_NAME:
            {
                // Read uuid from eeprom
                uint8 uuid_buf[UUID_LEN];
                eeprom_copy(uuid_buf, (const volatile uint8*)UUID, UUID_LEN);
                
                pushMessage(&RETURN_NAME, 1);
		        pushMessage(uuid_buf, UUID_LEN);
		        break;
            }
	        case REQUEST_CARD_SIGNATURE:
            {
                hydro_sign_keypair kp;
                uint8 signature[SIG_LEN];
		        uint8 nonce[NONCE_LEN];
		        uint8 pin[PIN_LEN];
                
                pullMessage(nonce, NONCE_LEN);
                pullMessage(pin, PIN_LEN);

                generate_keys(pin, &kp);
        		hydro_sign_create(signature, nonce, NONCE_LEN, CONTEXT, kp.sk);

                pushMessage(&RETURN_CARD_SIGNATURE, 1);
                pushMessage(signature, SIG_LEN);
        		break;
            }

    	    case REQUEST_NEW_PK:
            {
                hydro_sign_keypair kp;
		        uint8 pin[PIN_LEN];
                
                pullMessage(pin, PIN_LEN);
                
                generate_keys(pin, &kp);
                
                pushMessage(&RETURN_NEW_PK, 1);
                pushMessage(kp.pk, PK_LEN);
        		break;
            }

    	    default:
    	        break;
        }
	}	
}

/* [] END OF FILE */
