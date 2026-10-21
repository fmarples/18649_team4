#ifndef LAB3_ZONE_STATE_H
#define LAB3_ZONE_STATE_H
#include <stdbool.h>
#include <stdint.h>

/* Every supervision threshold lives here; pi/zone_state.py mirrors them.
 * R4.5: heartbeat every 20 ms, a zone fails after three missed periods on both
 * buses. R4.7: a bus is degraded when no peer heartbeat arrives on it for the
 * same three periods. CTRL follows the 20 ms proxy interval. */
#define HB_PERIOD_MS 20U
#define HB_TIMEOUT_MS 60U
#define CTRL_TIMEOUT_MS 60U
/* BLINK toggles every 500 ms; after this age an STM32 falls back to local hazards. */
#define BLINK_TIMEOUT_MS 750U
#define ZONE_SLOTS 4U /* indexed by zone id 1..3 */

/* Owned by one lock holder per node. Times are wrapping uptime milliseconds. */
struct zone_monitor {
    uint8_t self;
    bool hb_seen[ZONE_SLOTS][2];
    uint32_t hb_ms[ZONE_SLOTS][2];
    bool ctrl_seen;
    uint32_t ctrl_ms;
    /* Test button, bad CTRL or a received FAULT; only a FAULT clear releases it. */
    bool latched;
};

struct zone_health {
    bool alive[ZONE_SLOTS];  /* peer heartbeat fresh on at least one bus */
    bool bus_alive[2];       /* any peer heartbeat fresh on this bus */
    bool degraded[2];        /* bus silent after any heartbeat was ever seen */
    bool ctrl_fresh;
    bool error;
};

void zone_monitor_init(struct zone_monitor *m, uint8_t self);
/* Record per bus BEFORE duplicate filtering, or the second bus looks silent. */
void zone_monitor_heartbeat(struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t now_ms);
/* A valid in-range CTRL (STM32) or an accepted UDP update (Pi). */
void zone_monitor_ctrl(struct zone_monitor *m, uint32_t now_ms);
/* Lab 1 error state: power-up in error (nothing seen yet); out once both peers
 * are alive on some bus and CTRL is fresh; in on a latch, a failed peer or stale CTRL. */
struct zone_health zone_monitor_evaluate(const struct zone_monitor *m, uint32_t now_ms);
#endif
