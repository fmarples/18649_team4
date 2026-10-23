/* Host test for the production src/zone_state.c; no Zephyr or CAN hardware. */
#include "zone_state.h"
#include <assert.h>
#include <stdio.h>

static unsigned checks;
#define CHECK(x) do { assert(x); ++checks; } while (0)

/* A peer heartbeat is also traffic on that bus, as in dispatch. */
static void beat(struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t t)
{
    zone_monitor_traffic(m, bus, t);
    zone_monitor_heartbeat(m, zone, bus, t);
}

static void beat_all(struct zone_monitor *m, uint32_t t)
{
    for (uint8_t zone = 1; zone <= 3; ++zone)
        for (unsigned bus = 0; bus < 2; ++bus) beat(m, zone, bus, t);
}

int main(void)
{
    struct zone_monitor m;
    struct zone_health h;

    /* Power-up: in error and isolated, no degraded LEDs (R3, R4.7). */
    zone_monitor_init(&m, 3, 0);
    h = zone_monitor_evaluate(&m, 0);
    CHECK(h.error && h.isolated && !h.degraded[0] && !h.degraded[1]);

    /* R3: heartbeats alone are not enough; one valid CTRL is also required. */
    beat_all(&m, 10);
    CHECK(zone_monitor_evaluate(&m, 11).error);
    zone_monitor_ctrl(&m);
    h = zone_monitor_evaluate(&m, 12);
    CHECK(!h.error && !h.isolated && h.alive[1] && h.alive[2] && !h.degraded[0] && !h.degraded[1]);

    /* R3 lists no stale-CTRL trigger: no CTRL for a long time is not an error
     * while every peer heartbeat continues (N1 sends CTRL at least every 50 ms). */
    for (uint32_t t = 20; t <= 1000; t += 20) beat_all(&m, t);
    CHECK(!zone_monitor_evaluate(&m, 1001).error);

    /* Own heartbeat id is ignored: N3 cannot keep itself alive. */
    zone_monitor_heartbeat(&m, 3, 0, 1001);
    CHECK(!m.hb_seen[3][0]);

    /* R4.7: pull this node's A jumper at t=1001. A is degraded exactly 60 ms
     * after the last A traffic, the state stays OK on B. */
    CHECK(zone_monitor_next_change_ms(&m, 1001) == 59);
    for (uint32_t t = 1020; t <= 1040; t += 20) { beat(&m, 1, 1, t); beat(&m, 2, 1, t); }
    CHECK(zone_monitor_next_change_ms(&m, 1040) == 20);
    CHECK(!zone_monitor_evaluate(&m, 1059).degraded[0]);
    beat(&m, 1, 1, 1060); beat(&m, 2, 1, 1060);
    h = zone_monitor_evaluate(&m, 1060);
    CHECK(h.degraded[0] && !h.degraded[1] && !h.error && !h.bus_ok[0] && h.bus_ok[1]);

    /* Restore A: the first frame from any node clears it. */
    zone_monitor_traffic(&m, 0, 1065);
    h = zone_monitor_evaluate(&m, 1065);
    CHECK(!h.degraded[0] && h.bus_ok[0]);

    /* R4.7 counts any traffic, not only heartbeats: CTRL alone keeps A healthy. */
    zone_monitor_init(&m, 2, 0);
    beat_all(&m, 0); zone_monitor_ctrl(&m);
    for (uint32_t t = 20; t <= 200; t += 20) { beat(&m, 1, 1, t); beat(&m, 3, 1, t); zone_monitor_traffic(&m, 0, t); }
    CHECK(!zone_monitor_evaluate(&m, 200).degraded[0]);

    /* R4.5: a peer fails only after three missed heartbeats on both buses,
     * 3 x 22 ms = 66 ms at the +10 % period limit (clarification chain). */
    zone_monitor_init(&m, 2, 0);
    beat_all(&m, 0); zone_monitor_ctrl(&m);
    for (uint32_t t = 20; t <= 60; t += 20) beat(&m, 1, 0, t); /* N3 silent after t=0 */
    CHECK(!zone_monitor_evaluate(&m, 65).error);
    h = zone_monitor_evaluate(&m, 66);
    CHECK(h.error && !h.alive[3] && h.alive[1] && !h.isolated);
    /* ...and leaves it without a reset once the heartbeat returns. */
    beat(&m, 3, 1, 81);
    CHECK(!zone_monitor_evaluate(&m, 82).error);

    /* A latch holds error with every input healthy, until released. */
    m.latched = true;
    CHECK(zone_monitor_evaluate(&m, 82).error);
    m.latched = false;
    CHECK(!zone_monitor_evaluate(&m, 82).error);

    /* R4.7 isolation: no heartbeat from any zone on either bus for 60 ms. Both
     * buses silent is not "degraded", which needs traffic on the other bus. */
    beat_all(&m, 100);
    CHECK(!zone_monitor_evaluate(&m, 159).isolated);
    h = zone_monitor_evaluate(&m, 160);
    CHECK(h.isolated && h.error && !h.degraded[0] && !h.degraded[1]);
    CHECK(zone_monitor_next_change_ms(&m, 160) == UINT32_MAX);

    /* Relay gate: a sender counts as present on a bus while its heartbeat there
     * is under 60 ms old. Relaying a present sender's frame onto a two-node bus
     * can start bit-identical with the original; neither copy is then ACKed and
     * both retry in lockstep forever. */
    zone_monitor_init(&m, 2, 0);
    CHECK(!zone_monitor_present(&m, 1, 1, 0));          /* never heard: relay */
    beat(&m, 1, 1, 100);
    CHECK(zone_monitor_present(&m, 1, 1, 159));
    CHECK(!zone_monitor_present(&m, 1, 1, 160));        /* 60 ms silent: relay */
    CHECK(!zone_monitor_present(&m, 1, 0, 120));        /* per bus */
    CHECK(!zone_monitor_present(&m, 0, 1, 120));        /* unknown origin */
    CHECK(!zone_monitor_present(&m, 2, 1, 120));        /* self */

    /* Unsigned age survives the 32-bit uptime wrap. */
    zone_monitor_init(&m, 3, UINT32_MAX - 5);
    beat_all(&m, UINT32_MAX - 5); zone_monitor_ctrl(&m);
    CHECK(!zone_monitor_evaluate(&m, 10).error);
    CHECK(zone_monitor_evaluate(&m, 61).error);

    printf("PASS: %u zone-state checks\n", checks);
    return 0;
}
