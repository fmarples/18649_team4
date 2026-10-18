#ifndef LAB3_CAN_PROTOCOL_H
#define LAB3_CAN_PROTOCOL_H
#include <stdbool.h>
#include <stdint.h>
#include <zephyr/drivers/can.h>
#define ID_CTRL  0x010
#define ID_FAULT 0x020
#define ID_HB_N1 0x100
#define ID_HB_N2 0x101
#define ID_HB_N3 0x102
#define ID_BLINK 0x200
#define ID_FORCE 0x300
#define ZONE_N1 1
#define ZONE_N2 2
#define ZONE_N3 3
#define STATE_ERROR 0
#define STATE_OK 1
#define STATE_TEST 2
#define BLINK_OFF 0
#define BLINK_LEFT 1
#define BLINK_RIGHT 2
#define BLINK_HAZARD 3
uint8_t lab3_crc8(const uint8_t *data, unsigned length);
bool lab3_frame_valid(const struct can_frame *frame);
void lab3_seal(struct can_frame *frame);
void lab3_pack_heartbeat(struct can_frame *frame, uint32_t id, uint8_t seq, uint8_t state, bool bus_a, bool bus_b);
void lab3_pack_fault(struct can_frame *frame, uint8_t seq, uint8_t zone, uint8_t reason);
void lab3_pack_force(struct can_frame *frame, uint8_t seq, int8_t counter);
#endif
