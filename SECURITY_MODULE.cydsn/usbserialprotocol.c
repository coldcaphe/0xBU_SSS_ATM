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

#include "usbserialprotocol.h"

#define RECV_OK 0
#define RECV_ER 1

#define SYNC_TYPE_HSM 0x1C
#define SYNC_REQUEST_PROV 0x15
#define SYNC_REQUEST_NO_PROV 0x16
#define SYNC_FAILED_PROV 0x17
#define SYNC_FAILED_NO_PROV 0x18
#define SYNC_CONFIRMED_PROV 0x19
#define SYNC_CONFIRMED_NO_PROV 0x1A
#define SYNCED 0x1B
#define SYNC_TYPE_HSM_P 0x1C
#define SYNC_TYPE_HSM_P 0x3C
#define PSOC_DEVICE_REQUEST 0x1E


uint8 getValidByte()
{
    uint8 retval = 0u;
    while(DB_UART_SpiUartGetRxBufferSize() < 1); // wait for byte
    retval = DB_UART_UartGetByte();
    return retval;
}


int pushMessage(const uint8 data[], uint8 size)
{
    int i;

    DB_UART_UartPutChar(size);
    
    for (i = 0; i < size; i++) {
        DB_UART_UartPutChar(data[i]);   
    }
    
    return RECV_OK;
}

uint8 pullMessage(uint8 data[], uint8 length)
{
    uint8 i;
    for (i = 0; i < length; i++) {
        data[i] = getValidByte();   
    }

   return i;
}

/* 
 * synchronization protocol:
 *
 * 1) ATM -> "READY" -> PSoC
 * 2) if bad:  PSoC -> received bad message -> ATM; goto 1)
 *    if good: PSoC -> PSoC name (prov/norm) -> ATM
 * 3) ATM -> "GO" -> PSoC
 * 4) if bad: goto 1)
 */
void syncConnection(int prov) 
{
    uint8* message;
    
    do {
        pullMessage(message, (uint8)1);                              
        if (prov) {
            if (*message == SYNC_REQUEST_NO_PROV) {
                pushMessage((uint8*)SYNC_CONFIRMED_PROV, (uint8)1);
                return;
                
            }
            else if (*message == SYNC_REQUEST_PROV) {
                pushMessage((uint8*)SYNC_FAILED_PROV, (uint8)1);
                return;
            }
            else if (*message == PSOC_DEVICE_REQUEST) {
                pushMessage((uint8*)SYNC_TYPE_HSM_P, (uint8)1);
                return
            }
        }
        else {
            if (*message == SYNC_REQUEST_PROV) {
                pushMessage((uint8*)SYNC_CONFIRMED_NO_PROV, (uint8)1);
                return;
                
            }
            else if (*message == SYNC_REQUEST_NO_PROV) {
                pushMessage((uint8*)SYNC_FAILED_NO_PROV, (uint8)1);
                return;
            }
            else if (*message == PSOC_DEVICE_REQUEST) {
                pushMessage((uint8*)SYNC_TYPE_HSM_N, (uint8)1);
                return
            }
        }
    }
    
    while (*message != SYNCED);
}

/* [] END OF FILE */
