#include "project.h"

// Lengths of various protocol materials
#define PIN_LEN 8
#define UUID_LEN 36
#define R_LEN 32
#define NONCE_LEN 32
#define SIG_LEN 64
#define PK_LEN 32
#define RAND_KEY_LEN 32
#define SEED_LEN 32


// General enums for denoting that a request was accepted/rejected
static const uint8 ACCEPTED		            = 0x20;
static const uint8 REJECTED		            = 0x21;


// Constants for request types made to the card
#define REQUEST_NAME                        0x00
#define REQUEST_CARD_SIGNATURE              0x02
#define REQUEST_PROVISION                   0x26
#define REQUEST_NEW_PK                      0x0C


//static const uint8 INITIATE_PROVISION       = 0x25;
static const uint8 RETURN_NAME              = 0x01;
static const uint8 RETURN_CARD_SIGNATURE    = 0x03;
static const uint8 RETURN_NEW_PK            = 0x0D;


// Enums for syncing with ATM
static const uint8 SYNC_REQUEST_PROV        = 0x15;
static const uint8 SYNC_REQUEST_NO_PROV     = 0x16;
static const uint8 SYNC_CONFIRMED_PROV      = 0x17;
static const uint8 SYNC_CONFIRMED_NO_PROV   = 0x18;
static const uint8 SYNC_FAILED_NO_PROV      = 0x19;
static const uint8 SYNC_FAILED_PROV         = 0x1A;
static const uint8 SYNCED                   = 0x1B;
static const uint8 SYNC_TYPE_CARD_N         = 0x1D;
static const uint8 SYNC_TYPE_CARD_P         = 0x3D;
static const uint8 SYNC_TYPE_HSM_N          = 0x1C;
static const uint8 SYNC_TYPE_HSM_P          = 0x3C;
static const uint8 PSOC_DEVICE_REQUEST      = 0x1E;

// Constants for syncing
#define SYNC_NORM 0
#define SYNC_PROV 1


//context for libhydrogen functions
static const char CONTEXT[8] = {0, 0, 0, 0, 0, 0, 0, 0};


//I just wanted the compiler to stop yelling at me :(
static void eeprom_copy(uint8 *dst, const volatile uint8 *src, uint8 len) 
{
    for (int i = 0; i < len; i++) {
        dst[i] = src[i];
    }
}
