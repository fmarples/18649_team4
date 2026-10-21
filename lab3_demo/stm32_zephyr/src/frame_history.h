#ifndef LAB3_FRAME_HISTORY_H
#define LAB3_FRAME_HISTORY_H
#include <stdbool.h>
#include <stdint.h>

/* Ported from Tianyi's lab3-relay-immediate branch (commit a146752).
 *
 * Duplicate lifetime, NOT a wait before forwarding. It must exceed the worst
 * skew between the A copy, the B copy and a relayed copy (the measured Pi gap
 * between its can0 and can1 writes reaches 2.6 ms) and stay below the 320 ms
 * reuse time of a 4-bit sequence at 20 ms. Every catalog payload is idempotent,
 * so a copy that arrives after expiry is re-applied harmlessly.
 */
#define FRAME_HISTORY_MS 20U
#define FRAME_HISTORY_SIZE 32U
struct frame_key { uint16_t id; uint8_t source, seq; };
struct frame_record {
    struct frame_key key;
    uint32_t first_ms;
    uint8_t seen_buses, attempted_buses;
    bool valid;
};
struct frame_history { struct frame_record records[FRAME_HISTORY_SIZE]; };
enum frame_observation { FRAME_NEW, FRAME_DUPLICATE, FRAME_HISTORY_FULL };
enum relay_claim { RELAY_SEND, RELAY_SUPPRESS, RELAY_STALE };

/* Caller serializes all access. Only validated catalog frames may enter.
 * A same-bus repeat inside the lifetime is a relayed copy and is dropped; after
 * the lifetime the same (ID, seq) is a new message. */
enum frame_observation frame_observe(struct frame_history *h,
    struct frame_key key, unsigned bus, uint32_t received_ms);
/* Claim at most one attempt on the opposite bus. No heartbeat state is used.
 * first_ms is the original receive timestamp carried with the queued frame.
 * A known opposite-bus copy suppresses the send. */
enum relay_claim frame_claim_relay(struct frame_history *h,
    struct frame_key key, unsigned incoming_bus, uint32_t first_ms, uint32_t now_ms);
#endif
