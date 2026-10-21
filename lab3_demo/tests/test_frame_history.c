/* Host test for the production src/frame_history.c; no CAN hardware.
 * Adapted from Tianyi's lab3-relay-immediate test, expressed in FRAME_HISTORY_MS. */
#include "frame_history.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

#define W FRAME_HISTORY_MS
static struct frame_history h;
static struct frame_key ctrl = {0x010, 0, 7};
static unsigned checks;
#define CHECK(x) do { assert(x); ++checks; } while (0)
static void reset(void) { memset(&h, 0, sizeof(h)); }
int main(void)
{
    /* The very first CTRL can relay at the SAME time, with no heartbeat input. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, 0) == FRAME_NEW);
    CHECK(frame_claim_relay(&h, ctrl, 0, 0, 0) == RELAY_SEND);
    CHECK(frame_claim_relay(&h, ctrl, 0, 0, 0) == RELAY_SUPPRESS);

    /* A healthy destination copy that arrives before the worker avoids a send. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, ctrl, 1, 101) == FRAME_DUPLICATE);
    CHECK(frame_claim_relay(&h, ctrl, 0, 100, 101) == RELAY_SUPPRESS);

    /* Scenario (c): N3 sees only B; direct and relayed copies on B apply once. */
    reset();
    CHECK(frame_observe(&h, ctrl, 1, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, ctrl, 1, 101) == FRAME_DUPLICATE);
    CHECK(frame_observe(&h, ctrl, 0, 102) == FRAME_DUPLICATE);

    /* The Pi's measured 2.6 ms can0-to-can1 write gap stays inside the lifetime. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, ctrl, 1, 103) == FRAME_DUPLICATE);

    /* Reverse direction is also immediate. A return copy cannot bounce back. */
    reset();
    struct frame_key hb3 = {0x102, 0, 3};
    CHECK(frame_observe(&h, hb3, 1, 100) == FRAME_NEW);
    CHECK(frame_claim_relay(&h, hb3, 1, 100, 100) == RELAY_SEND);
    CHECK(frame_observe(&h, hb3, 0, 101) == FRAME_DUPLICATE);
    CHECK(frame_claim_relay(&h, hb3, 0, 100, 101) == RELAY_SUPPRESS);

    /* Other messages/sequences do not erase history of a pending duplicate. */
    reset();
    struct frame_key next = {0x010, 0, 8};
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, next, 0, 101) == FRAME_NEW);
    CHECK(frame_observe(&h, ctrl, 1, 102) == FRAME_DUPLICATE);

    /* FAULT shares an ID but has independent per-reporter sequence counters. */
    reset();
    struct frame_key f1 = {0x020, 1, 0}, f3 = {0x020, 3, 0};
    CHECK(frame_observe(&h, f1, 0, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, f3, 0, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, f1, 1, 101) == FRAME_DUPLICATE);

    /* 4-bit counter wraps after 16 updates; the same key is new again at 320 ms. */
    reset();
    for (unsigned n = 0; n <= 16; ++n) {
        struct frame_key k = {0x010, 0, (uint8_t)(n & 15)};
        CHECK(frame_observe(&h, k, 0, n * 20) == FRAME_NEW);
        CHECK(frame_claim_relay(&h, k, 0, n * 20, n * 20) == RELAY_SEND);
    }

    /* Expiry; duplicates never extend the original lifetime. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_NEW);
    CHECK(frame_observe(&h, ctrl, 1, 100 + W) == FRAME_DUPLICATE);
    CHECK(frame_observe(&h, ctrl, 1, 101 + W) == FRAME_NEW);
    CHECK(frame_claim_relay(&h, ctrl, 0, 100, 101 + W) == RELAY_STALE);
    CHECK(frame_claim_relay(&h, ctrl, 1, 101 + W, 101 + W) == RELAY_SEND);

    /* A stalled worker must not send an expired queued command. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_NEW);
    CHECK(frame_claim_relay(&h, ctrl, 0, 100, 101 + W) == RELAY_STALE);

    /* Unsigned age remains correct across the 32-bit uptime wrap. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, UINT32_MAX - 2) == FRAME_NEW);
    CHECK(frame_observe(&h, ctrl, 1, 1) == FRAME_DUPLICATE);
    CHECK(frame_observe(&h, ctrl, 1, W) == FRAME_NEW);

    /* Capacity exhaustion never evicts live duplicate/forwarding state. */
    reset();
    for (unsigned n = 0; n < FRAME_HISTORY_SIZE; ++n) {
        struct frame_key k = {(uint16_t)(0x100 + n), 0, 0};
        CHECK(frame_observe(&h, k, 0, 100) == FRAME_NEW);
    }
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_HISTORY_FULL);
    struct frame_key first = {0x100, 0, 0};
    CHECK(frame_observe(&h, first, 1, 100) == FRAME_DUPLICATE);
    CHECK(frame_observe(&h, ctrl, 0, 101 + W) == FRAME_NEW);

    /* A rejected submission is not retried for this key; later keys still relay. */
    reset();
    CHECK(frame_observe(&h, ctrl, 0, 100) == FRAME_NEW);
    CHECK(frame_claim_relay(&h, ctrl, 0, 100, 100) == RELAY_SEND);
    CHECK(frame_observe(&h, ctrl, 0, 101) == FRAME_DUPLICATE);
    CHECK(frame_claim_relay(&h, ctrl, 0, 100, 101) == RELAY_SUPPRESS);
    CHECK(frame_observe(&h, next, 0, 140) == FRAME_NEW);
    CHECK(frame_claim_relay(&h, next, 0, 140, 140) == RELAY_SEND);
    printf("PASS: %u frame-history checks\n", checks);
    return 0;
}
