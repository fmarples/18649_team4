#include "battery_guard.h"
void battery_guard_init(battery_guard *g) { *g = (battery_guard){0}; }
void battery_guard_sample(battery_guard *g, uint32_t now_ms, uint32_t pack_mv, bool valid)
{
    /* A new sample cannot hide a missed sampling deadline. Unsigned arithmetic
       handles the ordinary millisecond wrap; backward clocks also fail closed. */
    if (g->seen && (uint32_t)(now_ms - g->last_ms) > BATTERY_MAX_AGE_MS)
        g->fault = true;
    g->seen = true;
    g->last_ms = now_ms;
    g->pack_mv = pack_mv;
    if (!valid || pack_mv <= BATTERY_STOP_MV || pack_mv > BATTERY_MAX_MV)
        g->fault = true;
    if (g->fault) g->armed = false;
}
bool battery_guard_can_drive(battery_guard *g, uint32_t now_ms)
{
    if (!g->seen) return false;
    if ((uint32_t)(now_ms - g->last_ms) > BATTERY_MAX_AGE_MS) g->fault = true;
    if (g->fault) g->armed = false;
    return g->armed;
}
bool battery_guard_arm(battery_guard *g, uint32_t now_ms)
{
    (void)battery_guard_can_drive(g, now_ms);
    if (!g->seen || g->fault || g->pack_mv < BATTERY_ARM_MV) return false;
    g->armed = true;
    return true;
}
bool battery_adc_to_mv(uint16_t raw, uint16_t vdda_mv, uint32_t *pack_mv)
{
    if (!pack_mv || raw >= 4095u || vdda_mv < 2700u || vdda_mv > 3600u) return false;
    *pack_mv = ((uint32_t)raw * vdda_mv * 11u + 2047u) / 4095u;
    return true;
}
