#include "zone_state.h"
#include <string.h>

void zone_monitor_init(struct zone_monitor *m, uint8_t self, uint32_t now_ms)
{
    memset(m, 0, sizeof(*m));
    m->self = self;
    m->traffic_ms[0] = m->traffic_ms[1] = now_ms;
}

void zone_monitor_heartbeat(struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t now_ms)
{
    if (zone == 0 || zone >= ZONE_SLOTS || zone == m->self || bus > 1) return;
    m->hb_seen[zone][bus] = true;
    m->hb_ms[zone][bus] = now_ms;
}

void zone_monitor_traffic(struct zone_monitor *m, unsigned bus, uint32_t now_ms)
{
    if (bus <= 1) m->traffic_ms[bus] = now_ms;
}

void zone_monitor_ctrl(struct zone_monitor *m)
{
    m->ctrl_seen = true;
}

static bool fresh(bool seen, uint32_t stamp, uint32_t now, uint32_t limit)
{
    return seen && (uint32_t)(now - stamp) < limit;
}

bool zone_monitor_present(const struct zone_monitor *m, uint8_t zone, unsigned bus, uint32_t now_ms)
{
    if (zone == 0 || zone >= ZONE_SLOTS || zone == m->self || bus > 1) return false;
    return fresh(m->hb_seen[zone][bus], m->hb_ms[zone][bus], now_ms, BUS_SILENT_MS);
}

struct zone_health zone_monitor_evaluate(const struct zone_monitor *m, uint32_t now)
{
    struct zone_health h = {0};
    bool all_alive = true, heard = false;
    for (uint8_t zone = 1; zone < ZONE_SLOTS; ++zone) {
        if (zone == m->self) continue;
        for (unsigned bus = 0; bus < 2; ++bus) {
            h.alive[zone] |= fresh(m->hb_seen[zone][bus], m->hb_ms[zone][bus], now, ZONE_FAIL_MS);
            heard |= fresh(m->hb_seen[zone][bus], m->hb_ms[zone][bus], now, BUS_SILENT_MS);
        }
        all_alive &= h.alive[zone];
    }
    for (unsigned bus = 0; bus < 2; ++bus) h.bus_ok[bus] = fresh(true, m->traffic_ms[bus], now, BUS_SILENT_MS);
    for (unsigned bus = 0; bus < 2; ++bus) h.degraded[bus] = !h.bus_ok[bus] && h.bus_ok[bus ^ 1U];
    h.isolated = !heard;
    h.error = m->latched || !all_alive || h.isolated || !m->ctrl_seen;
    return h;
}

uint32_t zone_monitor_next_change_ms(const struct zone_monitor *m, uint32_t now)
{
    uint32_t next = UINT32_MAX;
    for (unsigned bus = 0; bus < 2; ++bus) {
        uint32_t age = now - m->traffic_ms[bus];
        if (age < BUS_SILENT_MS && BUS_SILENT_MS - age < next) next = BUS_SILENT_MS - age;
    }
    return next;
}
