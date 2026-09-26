#ifndef UDP_RECEIVER_H
#define UDP_RECEIVER_H

#include <stdint.h>

#define UDP_PORT 8000
#define WHEEL_PACKET_LEN 276

typedef struct {
    uint32_t counter;
    int32_t steering_raw;
    int32_t throttle_raw;
    int32_t brake_raw;
    uint32_t buttons;
} wheel_state_t;

/*
 * Receive one valid wheel packet.
 *
 * Returns:
 *   1 = packet received and decoded
 *   0 = no packet available / timeout
 *  -1 = socket or packet error
 */
int udp_receiver_open(void);
int udp_receiver_receive(wheel_state_t *state);
void udp_receiver_close(void);

#endif
