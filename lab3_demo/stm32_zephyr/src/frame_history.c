#include "frame_history.h"

static bool same(struct frame_key a, struct frame_key b)
{
    return a.id == b.id && a.source == b.source && a.seq == b.seq;
}
static bool live(const struct frame_record *r, uint32_t now)
{
    return r->valid && (uint32_t)(now - r->first_ms) <= FRAME_HISTORY_MS;
}
enum frame_observation frame_observe(struct frame_history *h,
    struct frame_key key, unsigned bus, uint32_t received_ms)
{
    struct frame_record *free_slot = 0;
    if (bus > 1) return FRAME_HISTORY_FULL;
    for (unsigned i = 0; i < FRAME_HISTORY_SIZE; ++i) {
        struct frame_record *r = &h->records[i];
        if (!live(r, received_ms)) {
            if (!free_slot) free_slot = r;
        } else if (same(r->key, key)) {
            r->seen_buses |= (uint8_t)(1U << bus);
            /* Do not extend expiry on a duplicate: repeats cannot keep a key
             * alive forever and suppress a new sequence generation. */
            return FRAME_DUPLICATE;
        }
    }
    /* Never evict live history to make room: that could re-admit a duplicate. */
    if (!free_slot) return FRAME_HISTORY_FULL;
    *free_slot = (struct frame_record){.key=key, .first_ms=received_ms,
        .seen_buses=(uint8_t)(1U << bus), .valid=true};
    return FRAME_NEW;
}
enum relay_claim frame_claim_relay(struct frame_history *h,
    struct frame_key key, unsigned incoming_bus, uint32_t first_ms, uint32_t now_ms)
{
    if (incoming_bus > 1) return RELAY_STALE;
    const uint8_t destination = (uint8_t)(1U << (incoming_bus ^ 1U));
    for (unsigned i = 0; i < FRAME_HISTORY_SIZE; ++i) {
        struct frame_record *r = &h->records[i];
        if (!live(r, now_ms) || !same(r->key, key) || r->first_ms != first_ms) continue;
        if ((r->seen_buses | r->attempted_buses) & destination) return RELAY_SUPPRESS;
        r->attempted_buses |= destination;
        return RELAY_SEND;
    }
    /* Do not forward an expired queue entry using a newer generation's record. */
    return RELAY_STALE;
}
