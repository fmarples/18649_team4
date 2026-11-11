#ifndef LAB5_WIRE_H
#define LAB5_WIRE_H
#include "lab5.h"
#define L5_REF_BASE 0x080U
#define L5_RPC_BASE 0x400U
struct l5_packet {
    uint16_t id;
    uint8_t data[8];
};
struct l5_rx_slot {
    uint8_t seq, mask;
    bool seen, delivered;
    uint64_t time_ms;
    uint8_t data[L5_RPC_SIZE];
};
struct l5_wire {
    uint8_t seq;
    /* A reconnecting bus can drain older queued frames after sequence wrap.
     * Its assembly/sequence state must never suppress the healthy bus. */
    struct l5_rx_slot rx[2][4][4];
    uint32_t rejected, duplicates;
};
void l5_fragment(struct l5_wire *, const struct l5_rpc *, struct l5_packet out[4]);
bool l5_assemble(struct l5_wire *, unsigned bus, const struct l5_packet *, uint64_t now_ms,
                 struct l5_rpc *);
void l5_ref_pack(struct l5_packet *, uint8_t src, uint8_t cycle, uint16_t term, uint32_t time_us);
bool l5_ref_unpack(const struct l5_packet *, uint8_t *src, uint8_t *cycle, uint16_t *term,
                   uint32_t *time_us);
#endif
