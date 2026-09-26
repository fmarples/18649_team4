#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/*
 * LAB 2 UART PROTOCOL
 *
 * This protocol is a team design choice. It is NOT specified by the lab handout.
 *
 * Command frame, 15 bytes:
 *   [0]     0xAA             sync/start byte
 *   [1]     0x01             frame type = COMMAND
 *   [2:3]   sequence         little-endian uint16
 *   [4:5]   steering         signed int16, raw wheel value
 *   [6:7]   throttle        signed int16, raw wheel value
 *   [8:9]   brake            signed int16, raw wheel value
 *   [10:13] buttons          uint32 bit mask
 *   [14]    checksum         8-bit additive checksum
 *
 * Status frame, 12 bytes:
 *   [0]     0xAA             sync/start byte
 *   [1]     0x02             frame type = STATUS
 *   [2:3]   sequence
 *   [4:5]   motor1_current   raw ADC/current-sensor value
 *   [6:7]   motor2_current   raw ADC/current-sensor value
 *   [8:9]   servo_current    raw ADC/current-sensor value
 *   [10]    zone_state       application state
 *   [11]    checksum
 *
 * Before using this on hardware, agree with the team on:
 *   - baud rate
 *   - whether these values remain raw or are scaled
 *   - button bit assignments
 *   - checksum/CRC choice
 *   - exact state values
 */

#define UART_SYNC             0xAAu
#define UART_FRAME_COMMAND    0x01u
#define UART_FRAME_STATUS     0x02u

#define UART_COMMAND_LEN      15u
#define UART_STATUS_LEN       12u

#define UART_BAUDRATE         115200u

#define ZONE_ERROR            0u
#define ZONE_NORMAL           1u

static inline uint8_t protocol_checksum(const uint8_t *data, uint8_t len)
{
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; ++i) {
        sum = (uint8_t)(sum + data[i]);
    }
    return sum;
}

#endif
