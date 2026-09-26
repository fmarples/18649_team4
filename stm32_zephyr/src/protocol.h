#ifndef PROTOCOL_H
#define PROTOCOL_H
#include <stdint.h>
#define UART_SYNC 0xAAu
#define FRAME_COMMAND 0x01u
#define FRAME_STATUS  0x02u
#define UART_COMMAND_LEN 15u
#define UART_STATUS_LEN 12u
#define UART_BAUDRATE 115200u
#define ZONE_ERROR 0u
#define ZONE_NORMAL 1u

typedef struct {
    uint8_t type;
    uint16_t sequence;
    int16_t steering;
    int16_t throttle;
    int16_t brake;
    uint32_t buttons;
} command_frame_t;

typedef struct {
    uint8_t type;
    uint16_t sequence;
    uint16_t motor1_current;
    uint16_t motor2_current;
    uint16_t servo_current;
    uint8_t state;
} status_frame_t;

static inline uint8_t protocol_checksum(const uint8_t *data, uint8_t len) {
    uint8_t sum=0; for (uint8_t i=0;i<len;i++) sum=(uint8_t)(sum+data[i]); return sum;
}
#endif
