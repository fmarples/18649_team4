#include "wire.h"
#include <string.h>
void l5_fragment(struct l5_wire *w, const struct l5_rpc *m, struct l5_packet out[4]) {
    uint8_t p[L5_RPC_SIZE];
    l5_encode(m, p);
    uint8_t seq = w->seq++;
    for (unsigned f = 0; f < 4; f++) {
        out[f].id = (uint16_t)(L5_RPC_BASE + (m->src << 4) + (m->dst << 2) + f);
        out[f].data[0] = seq;
        memcpy(out[f].data + 1, p + f * 6, 6);
        out[f].data[7] = l5_crc(out[f].data, 7);
    }
}
bool l5_assemble(struct l5_wire *w, const struct l5_packet *p, uint64_t now, struct l5_rpc *m) {
    if (p->id < 0x410 || p->id > 0x43f || l5_crc(p->data, 7) != p->data[7]) {
        w->rejected++;
        return false;
    }
    uint8_t src = (p->id >> 4) & 3, dst = (p->id >> 2) & 3, f = p->id & 3, seq = p->data[0];
    struct l5_rx_slot *s = &w->rx[src][dst];
    if (!s->seen || now - s->time_ms > 250 || (seq != s->seq && (uint8_t)(seq - s->seq) < 128)) {
        s->seq = seq;
        s->mask = 0;
        s->delivered = false;
        s->seen = true;
        s->time_ms = now;
    }
    if (s->seq != seq || s->delivered) {
        w->duplicates++;
        return false;
    }
    if (s->mask & (1U << f)) {
        if (memcmp(s->data + 6 * f, p->data + 1, 6)) {
            w->rejected++;
            s->delivered = true;
        } else
            w->duplicates++;
        return false;
    }
    memcpy(s->data + 6 * f, p->data + 1, 6);
    s->mask |= 1U << f;
    if (s->mask != 15)
        return false;
    s->delivered = true;
    if (!l5_decode(m, s->data) || m->src != src || m->dst != dst) {
        w->rejected++;
        return false;
    }
    return true;
}
void l5_ref_pack(struct l5_packet *p, uint8_t src, uint8_t cycle, uint16_t term, uint32_t t) {
    p->id = L5_REF_BASE + src;
    p->data[0] = cycle;
    p->data[1] = (uint8_t)term;
    p->data[2] = (uint8_t)(term >> 8);
    for (unsigned i = 0; i < 4; i++)
        p->data[3 + i] = (uint8_t)(t >> (8 * i));
    p->data[7] = l5_crc(p->data, 7);
}
bool l5_ref_unpack(const struct l5_packet *p, uint8_t *src, uint8_t *cycle, uint16_t *term,
                   uint32_t *t) {
    if (p->id < 0x81 || p->id > 0x83 || p->data[7] != l5_crc(p->data, 7))
        return false;
    *src = (uint8_t)(p->id - L5_REF_BASE);
    *cycle = p->data[0];
    *term = p->data[1] | ((uint16_t)p->data[2] << 8);
    *t = 0;
    for (unsigned i = 0; i < 4; i++)
        *t |= (uint32_t)p->data[3 + i] << (8 * i);
    return *term > 0 && *term <= L5_TERM_MAX;
}
