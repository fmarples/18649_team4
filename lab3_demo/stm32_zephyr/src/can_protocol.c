/* Lab 3 CAN payload serialization and CRC-8/ATM. Do not send C structs directly. */
#include "can_protocol.h"
#include <string.h>

uint8_t lab3_crc8(const uint8_t *data, unsigned length)
{
    uint8_t crc = 0;
    for (unsigned i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc & 0x80U) ? (uint8_t)((crc << 1) ^ 0x07U) : (uint8_t)(crc << 1);
    }
    return crc;
}

bool lab3_frame_valid(const struct can_frame *frame)
{
    return frame && !(frame->flags & (CAN_FRAME_IDE | CAN_FRAME_RTR | CAN_FRAME_FDF)) &&
        frame->dlc == 8 && lab3_crc8(frame->data, 7) == frame->data[7];
}

void lab3_seal(struct can_frame *frame)
{
    frame->dlc = 8;
    frame->data[7] = lab3_crc8(frame->data, 7);
}

static void start(struct can_frame *f, uint32_t id)
{
    memset(f, 0, sizeof(*f));
    f->id = id;
    f->dlc = 8;
}

void lab3_pack_heartbeat(struct can_frame *f, uint32_t id, uint8_t state, bool a, bool b)
{
    start(f, id);
    f->data[1] = state;
    f->data[2] = (a ? 1 : 0) | (b ? 2 : 0);
}

void lab3_pack_fault(struct can_frame *f, uint8_t failing_zone, enum fault_reason reason, uint8_t reporter)
{
    start(f, ID_FAULT);
    f->data[1] = failing_zone;
    f->data[2] = (uint8_t)reason;
    f->data[3] = reporter;
}

void lab3_pack_force(struct can_frame *f, int8_t counter)
{
    start(f, ID_FORCE);
    f->data[1] = (uint8_t)counter;
}

bool lab3_ctrl_decode(const struct can_frame *f, struct lab3_ctrl *out)
{
    /* b0 seq/flags, b1..2 steer LE, b3 throttle %, b4 brake %, b5 buttons, b6 reserved. */
    if ((f->data[0] >> 4) != CTRL_FLAGS || f->data[6] != 0 || f->data[3] > 100 || f->data[4] > 100)
        return false;
    out->steer = (int16_t)(f->data[1] | (f->data[2] << 8));
    out->throttle = f->data[3];
    out->brake = f->data[4];
    out->buttons = f->data[5];
    return true;
}

uint8_t lab3_heartbeat_zone(uint32_t id)
{
    switch (id) {
    case ID_HB_N1: return ZONE_N1;
    case ID_HB_N2: return ZONE_N2;
    case ID_HB_N3: return ZONE_N3;
    default: return 0;
    }
}

uint8_t lab3_frame_origin(const struct can_frame *f)
{
    switch (f->id) {
    case ID_CTRL: case ID_BLINK: case ID_HB_N1: return ZONE_N1;
    case ID_HB_N2: case ID_FORCE: return ZONE_N2;
    case ID_HB_N3: return ZONE_N3;
    case ID_FAULT: return f->data[3] >= ZONE_N1 && f->data[3] <= ZONE_N3 ? f->data[3] : 0;
    default: return 0;
    }
}

uint8_t lab3_dedup_source(const struct can_frame *f)
{
    return f->id == ID_FAULT ? f->data[3] : 0;
}
