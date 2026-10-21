#include "zone_state.h"
#include <string.h>

void zone_monitor_init(struct zone_monitor *m, uint8_t self)
{
    memset(m, 0, sizeof(*m));
    m->self = self;
}

void zone_monitor_heartbeat(struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t now_ms)
{
    if (zone == 0 || zone >= ZONE_SLOTS || zone == m->self || bus > 1) return;
    m->hb_seen[zone][bus] = true;
    m->hb_ms[zone][bus] = now_ms;
}

void zone_monitor_ctrl(struct zone_monitor *m, uint32_t now_ms)
{
    m->ctrl_seen = true;
    m->ctrl_ms = now_ms;
}

static bool fresh(bool seen, uint32_t stamp, uint32_t now, uint32_t limit)
{
    return seen && (uint32_t)(now - stamp) < limit;
}

struct zone_health zone_monitor_evaluate(const struct zone_monitor *m, uint32_t now)
{
    struct zone_health h = {0};
    bool ever_seen = false, all_alive = true;
    for (uint8_t zone = 1; zone < ZONE_SLOTS; ++zone) {
        if (zone == m->self) continue;
        for (unsigned bus = 0; bus < 2; ++bus) {
            bool alive = fresh(m->hb_seen[zone][bus], m->hb_ms[zone][bus], now, HB_TIMEOUT_MS);
            h.bus_alive[bus] |= alive;
            h.alive[zone] |= alive;
            ever_seen |= m->hb_seen[zone][bus];
        }
        all_alive &= h.alive[zone];
    }
    /* A node that has never heard anyone cannot tell a bus fault from absent peers. */
    for (unsigned bus = 0; bus < 2; ++bus) h.degraded[bus] = ever_seen && !h.bus_alive[bus];
    h.ctrl_fresh = fresh(m->ctrl_seen, m->ctrl_ms, now, CTRL_TIMEOUT_MS);
    h.error = m->latched || !all_alive || !h.ctrl_fresh;
    return h;
}
