/* Host test for the production src/zone_state.c; no Zephyr or CAN hardware. */
#include "zone_state.h"
#include <assert.h>
#include <stdio.h>

static unsigned checks;
#define CHECK(x) do { assert(x); ++checks; } while (0)

static void beat(struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t t)
{
    zone_monitor_heartbeat(m, zone, bus, t);
}

int main(void)
{
    struct zone_monitor m;
    struct zone_health h;

    /* Power-up: in error, no degraded LEDs before any heartbeat is heard. */
    zone_monitor_init(&m, 3);
    h = zone_monitor_evaluate(&m, 0);
    CHECK(h.error && !h.degraded[0] && !h.degraded[1]);

    /* Heartbeats alone are not enough; a valid CTRL is also required. */
    beat(&m, 1, 0, 10); beat(&m, 2, 0, 10); beat(&m, 1, 1, 10); beat(&m, 2, 1, 10);
    CHECK(zone_monitor_evaluate(&m, 11).error);
    zone_monitor_ctrl(&m, 11);
    h = zone_monitor_evaluate(&m, 12);
    CHECK(!h.error && h.alive[1] && h.alive[2] && !h.degraded[0] && !h.degraded[1]);

    /* Own heartbeat id is ignored: N3 cannot keep itself alive. */
    beat(&m, 3, 0, 12);
    CHECK(!m.hb_seen[3][0]);

    /* Pull this node's A jumper: A goes degraded at 60 ms, state stays OK on B. */
    for (uint32_t t = 30; t <= 50; t += 20) { beat(&m, 1, 1, t); beat(&m, 2, 1, t); zone_monitor_ctrl(&m, t); }
    h = zone_monitor_evaluate(&m, 69);
    CHECK(!h.degraded[0]);
    h = zone_monitor_evaluate(&m, 70);
    CHECK(h.degraded[0] && !h.degraded[1] && !h.error);

    /* Restore A: the LED clears on the first heartbeat. */
    beat(&m, 2, 0, 95);
    h = zone_monitor_evaluate(&m, 95);
    CHECK(!h.degraded[0] && h.bus_alive[0]);

    /* One peer still on A keeps A healthy even when the other peer left A. */
    CHECK(h.alive[1] && h.alive[2]);

    /* A peer silent on BOTH buses for 60 ms fails the zone and enters error. */
    zone_monitor_init(&m, 2);
    beat(&m, 1, 0, 0); beat(&m, 3, 0, 0); beat(&m, 3, 1, 0); zone_monitor_ctrl(&m, 0);
    beat(&m, 1, 0, 40); zone_monitor_ctrl(&m, 40);
    CHECK(!zone_monitor_evaluate(&m, 59).error);
    h = zone_monitor_evaluate(&m, 60);
    CHECK(h.error && !h.alive[3] && h.alive[1]);
    /* ...and leaves it without a reset once the heartbeat returns. */
    beat(&m, 3, 1, 61); zone_monitor_ctrl(&m, 61);
    CHECK(!zone_monitor_evaluate(&m, 62).error);

    /* Stale CTRL (proxy stopped) enters error while heartbeats continue. */
    beat(&m, 1, 0, 100); beat(&m, 3, 0, 100);
    CHECK(!zone_monitor_evaluate(&m, 120).error);
    CHECK(zone_monitor_evaluate(&m, 125).error);

    /* A latch holds error with every input healthy, until released. */
    zone_monitor_ctrl(&m, 125);
    m.latched = true;
    CHECK(zone_monitor_evaluate(&m, 126).error);
    m.latched = false;
    CHECK(!zone_monitor_evaluate(&m, 126).error);

    /* Isolation: both buses silent lights both degraded LEDs. */
    h = zone_monitor_evaluate(&m, 200);
    CHECK(h.error && h.degraded[0] && h.degraded[1]);

    /* Unsigned age survives the 32-bit uptime wrap. */
    zone_monitor_init(&m, 3);
    beat(&m, 1, 0, UINT32_MAX - 5); beat(&m, 2, 0, UINT32_MAX - 5); zone_monitor_ctrl(&m, UINT32_MAX - 5);
    CHECK(!zone_monitor_evaluate(&m, 10).error);
    CHECK(zone_monitor_evaluate(&m, 60).error);

    printf("PASS: %u zone-state checks\n", checks);
    return 0;
}
