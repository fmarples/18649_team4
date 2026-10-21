#ifndef LAB3_DEMO_CAN_PROTOCOL_H
#define LAB3_DEMO_CAN_PROTOCOL_H
/* Lab 3 template catalog wire format; pi/can_protocol.py is the other half.
 * Standard IDs, DLC 8. Byte 0: low nibble per-ID sequence, high nibble flags.
 * Byte 7: CRC-8/ATM (poly 0x07, init 0) over bytes 0..6. */
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
#define BLINK_OFF 0
#define BLINK_LEFT 1
#define BLINK_RIGHT 2
#define BLINK_HAZARD 3
#define CTRL_FLAGS 1 /* required high nibble of CTRL byte 0 */

/* FAULT byte 2. Clear releases every latch; ZONE_LOST is informational because
 * each receiver detects heartbeat loss itself and must recover without a clear. */
enum fault_reason {
    FAULT_CLEAR = 0,
    FAULT_TEST_BUTTON = 1,
    FAULT_BAD_CRC = 2,
    FAULT_BAD_CTRL = 3,
    FAULT_ZONE_LOST = 4,
};

/* Team-defined CTRL value ranges: steering is any int16; pedals are 0..100 %. */
struct lab3_ctrl { int16_t steer; uint8_t throttle, brake, buttons; };

uint8_t lab3_crc8(const uint8_t *data, unsigned length);
/* Standard data frame, DLC 8 and matching CRC. */
bool lab3_frame_valid(const struct can_frame *frame);
void lab3_seal(struct can_frame *frame);
/* Builders leave the sequence nibble zero; the send helper assigns it and seals. */
void lab3_pack_heartbeat(struct can_frame *frame, uint32_t id, uint8_t state, bool bus_a_ok, bool bus_b_ok);
/* FAULT bytes 1..3: failing zone, reason, reporting zone. */
void lab3_pack_fault(struct can_frame *frame, uint8_t failing_zone, enum fault_reason reason, uint8_t reporter);
void lab3_pack_force(struct can_frame *frame, int8_t counter);
/* Decodes a CRC-valid CTRL; false when any field is outside the values table. */
bool lab3_ctrl_decode(const struct can_frame *frame, struct lab3_ctrl *out);
/* Zone whose heartbeat this ID is, or 0. */
uint8_t lab3_heartbeat_zone(uint32_t id);
/* Zone that originated this frame (FAULT: reporter), or 0 when unknown. */
uint8_t lab3_frame_origin(const struct can_frame *frame);
/* FAULT has several senders with independent sequence counters. */
uint8_t lab3_dedup_source(const struct can_frame *frame);
#endif
