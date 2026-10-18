#ifndef LAB3_FRAME_HISTORY_H
#define LAB3_FRAME_HISTORY_H
#include <stdbool.h>
#include <stdint.h>

/* This is a duplicate lifetime, NOT a wait before forwarding. It retains the
 * candidate's 5 ms skew allowance. Measure it against actual A/B/relay delays.
 * It must stay below the minimum time to reuse a 4-bit sequence (320 ms at 20 ms).
 * A reboot that reuses an ID/sequence inside this window is indistinguishable.
 */
#define FRAME_HISTORY_MS 5U
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

/* Caller serializes all access. Only validated catalog frames may enter. */
enum frame_observation frame_observe(struct frame_history *h,
    struct frame_key key, unsigned bus, uint32_t received_ms);
/* Claim at most one attempt on the opposite bus. No heartbeat state is used.
 * first_ms is the original receive timestamp carried with the queued frame.
 * No timer/wait is started; a known opposite-bus copy suppresses the send.
 */
enum relay_claim frame_claim_relay(struct frame_history *h,
    struct frame_key key, unsigned incoming_bus, uint32_t first_ms, uint32_t now_ms);
#endif
