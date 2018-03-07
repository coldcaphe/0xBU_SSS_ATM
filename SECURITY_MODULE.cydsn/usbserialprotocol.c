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
#include "common.h"

uint8 getValidByte()
{
    uint8 retval = 0u;
    while(DB_UART_SpiUartGetRxBufferSize() < 1); // wait for byte
    retval = DB_UART_UartGetByte();
    return retval;
}


void pushMessage(const uint8 data[], uint8 size)
{
    for (uint8 i = 0; i < size; i++) {
        DB_UART_UartPutChar(data[i]);   
    }
}

void pullMessage(uint8 data[], uint8 length)
{
    for (uint8 i = 0; i < length; i++) {
        data[i] = getValidByte();   
    }
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
    uint8 message[1];
    
    do {
        pullMessage(message, (uint8)1);                              
        if (prov) {
            if (message[0] == SYNC_REQUEST_NO_PROV) {
                pushMessage(&SYNC_CONFIRMED_PROV, (uint8)1);
            }
            else if (message[0] == SYNC_REQUEST_PROV) {
                pushMessage(&SYNC_CONFIRMED_NO_PROV, (uint8)1);
            }
            else if (message[0] == PSOC_DEVICE_REQUEST) {
                pushMessage(&SYNC_TYPE_HSM_P, (uint8)1);
            }
        }
        else {
            if (message[0] == SYNC_REQUEST_PROV) {
                pushMessage(&SYNC_CONFIRMED_PROV, (uint8)1);
            }
            else if (message[0] == SYNC_REQUEST_NO_PROV) {
                pushMessage(&SYNC_CONFIRMED_PROV, (uint8)1);
            }
            else if (message[0] == PSOC_DEVICE_REQUEST) {
                pushMessage(&SYNC_TYPE_HSM_N, (uint8)1);
            }
        }
    }
    while (message[0] != SYNCED);
    
}

/* [] END OF FILE */
