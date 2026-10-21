/* Host stand-in for the parts of Zephyr's CAN API that can_protocol.c uses. */
#ifndef FAKE_ZEPHYR_DRIVERS_CAN_H
#define FAKE_ZEPHYR_DRIVERS_CAN_H
#include <stdint.h>
#define CAN_FRAME_IDE (1U << 0)
#define CAN_FRAME_RTR (1U << 1)
#define CAN_FRAME_FDF (1U << 2)
struct can_frame { uint32_t id; uint8_t dlc; uint8_t flags; uint8_t data[8]; };
#endif
