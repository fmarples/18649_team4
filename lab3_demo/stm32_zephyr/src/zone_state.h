#ifndef LAB3_ZONE_STATE_H
#define LAB3_ZONE_STATE_H
#include <stdbool.h>
#include <stdint.h>

/* Every supervision threshold lives here; pi/zone_state.py mirrors them.
 * R4.5: heartbeat every 20 ms (+/-10 %); a zone fails only after three
 * consecutive missed heartbeats on both buses, 3 x 22 ms = 66 ms at the period
 * limit (the clarification's error chain uses the same 66 ms).
 * R4.7: a bus is degraded after three heartbeat periods (60 ms) without traffic
 * from any other node while the other bus still has traffic; a zone that hears
 * no heartbeat from any other zone on either bus for 60 ms is isolated. */
#define HB_PERIOD_MS 20U
#define ZONE_FAIL_MS 66U
#define BUS_SILENT_MS 60U
/* BLINK arrives at least every 500 ms; older than this, N1 is unreachable. */
#define BLINK_TIMEOUT_MS 750U
#define ZONE_SLOTS 4U /* indexed by zone id 1..3 */

/* Owned by one lock holder per node. Times are wrapping uptime milliseconds. */
struct zone_monitor {
    uint8_t self;
    bool hb_seen[ZONE_SLOTS][2];
    uint32_t hb_ms[ZONE_SLOTS][2];
    uint32_t traffic_ms[2]; /* last frame from any other node; boot time until then */
    bool ctrl_seen;         /* R3: one valid CTRL is needed to leave power-up error */
    /* Test button, bad CTRL or a received FAULT; only a FAULT clear releases it. */
    bool latched;
};

struct zone_health {
    bool alive[ZONE_SLOTS]; /* peer heartbeat within ZONE_FAIL_MS on some bus */
    bool bus_ok[2];         /* traffic within BUS_SILENT_MS; heartbeat health bits */
    bool degraded[2];       /* R4.7 per-bus status LED */
    bool isolated;          /* R4.7: own fail-safe (motor braked, steering held, hazards) */
    bool error;
};

void zone_monitor_init(struct zone_monitor *m, uint8_t self, uint32_t now_ms);
/* Record per bus BEFORE duplicate filtering, or the second bus looks silent. */
void zone_monitor_heartbeat(struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t now_ms);
/* Any frame received from another node on this bus, valid or not. */
void zone_monitor_traffic(struct zone_monitor *m, unsigned bus, uint32_t now_ms);
/* A valid in-range CTRL arrived. */
void zone_monitor_ctrl(struct zone_monitor *m);
/* Relay gate: true while `zone`'s heartbeat on `bus` is under BUS_SILENT_MS old.
 * N2 forwards only frames whose origin is absent from the destination bus. */
bool zone_monitor_present(const struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t now_ms);
/* Lab 1 R3 error state: power-up in error; out once both peers are alive on
 * some bus and a valid CTRL has arrived; in on a latch, a failed peer or isolation. */
struct zone_health zone_monitor_evaluate(const struct zone_monitor *m, uint32_t now_ms);
/* Milliseconds until a bus with traffic reaches BUS_SILENT_MS, or UINT32_MAX.
 * Dispatch waits on it so DEG_x lights at exactly 60 ms, not on the next HB_MON. */
uint32_t zone_monitor_next_change_ms(const struct zone_monitor *m, uint32_t now_ms);
#endif
