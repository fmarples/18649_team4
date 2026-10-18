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
    return frame && frame->dlc == 8 && lab3_crc8(frame->data, 7) == frame->data[7];
}
void lab3_seal(struct can_frame *frame) { frame->dlc = 8; frame->data[7] = lab3_crc8(frame->data, 7); }
void lab3_pack_heartbeat(struct can_frame *f, uint32_t id, uint8_t seq, uint8_t state, bool a, bool b)
{
    memset(f, 0, sizeof(*f)); f->id = id; f->flags = 0; f->dlc = 8;
    f->data[0] = seq & 0x0F; f->data[1] = state; f->data[2] = (a ? 1 : 0) | (b ? 2 : 0); lab3_seal(f);
}
void lab3_pack_fault(struct can_frame *f, uint8_t seq, uint8_t zone, uint8_t reason)
{
    memset(f, 0, sizeof(*f)); f->id = ID_FAULT; f->flags = 0; f->dlc = 8;
    f->data[0] = seq & 0x0F; f->data[1] = zone; f->data[2] = reason; lab3_seal(f);
}
void lab3_pack_force(struct can_frame *f, uint8_t seq, int8_t counter)
{
    memset(f, 0, sizeof(*f)); f->id = ID_FORCE; f->flags = 0; f->dlc = 8;
    f->data[0] = seq & 0x0F; f->data[1] = (uint8_t)counter; lab3_seal(f);
}
