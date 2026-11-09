#include "lab5.h"
#include <math.h>
#include <string.h>
void l5_clock_init(struct l5_clock *c, uint64_t raw) {
    memset(c, 0, sizeof(*c));
    c->local_anchor = raw;
    c->global_anchor = raw;
    c->rate = 1.0;
}
static uint64_t estimate(const struct l5_clock *c, uint64_t raw) {
    return c->global_anchor + (uint64_t)((raw - c->local_anchor) * c->rate);
}
uint64_t l5_global(struct l5_clock *c, uint64_t raw) {
    uint64_t t = estimate(c, raw);
    if (t < c->last_return)
        t = c->last_return;
    c->last_return = t;
    return t;
}
void l5_clock_lead(struct l5_clock *c, uint8_t id, uint16_t term, uint64_t raw) {
    c->global_anchor = l5_global(c, raw);
    c->local_anchor = raw;
    c->leader = id;
    c->term = term;
    c->synced = true;
    c->have_pair = false;
}
bool l5_clock_ref(struct l5_clock *c, uint8_t leader, uint16_t term, uint32_t low, uint64_t raw,
                  uint32_t delay) {
    if (raw < c->local_anchor || !leader || term < c->term)
        return false;
    uint64_t predicted = estimate(c, raw);
    /* Extend the wrapping 32-bit wire clock to the closest 64-bit epoch. */
    int64_t delta = (int32_t)(low - (uint32_t)predicted);
    int64_t target = (int64_t)predicted + delta + delay;
    if (!c->synced) {
        target = c->have_epoch
                     ? (int64_t)c->epoch_hint + (int32_t)(low - (uint32_t)c->epoch_hint) + delay
                     : (int64_t)(uint64_t)low + delay;
    }
    if (target < 0) {
        c->rejected++;
        return false;
    }
    uint64_t master = (uint64_t)target;
    bool same = c->leader == leader && c->term == term;
    if (same && c->have_pair) {
        if (raw <= c->last_local || master <= c->last_master) {
            c->rejected++;
            return false;
        }
        double ratio = (double)(master - c->last_master) / (double)(raw - c->last_local);
        /* Reject queue spikes from the frequency estimator, still phase-correct.
         * This is a filter range, not a claim about oscillator specifications. */
        if (ratio > 0.99 && ratio < 1.01)
            c->rate = c->samples > 1 ? 0.9 * c->rate + 0.1 * ratio : ratio;
    }
    c->last_error = (int64_t)master - (int64_t)predicted;
    if (!c->synced) {
        c->global_anchor = master;
        c->last_return = master;
    } else {
        /* Limit each phase correction to 50 us, including a new leader. A
         * negative correction never makes global_gettime() go backwards. */
        int64_t step = c->last_error;
        if (step > 50)
            step = 50;
        if (step < -50)
            step = -50;
        c->global_anchor = (uint64_t)((int64_t)predicted + step);
    }
    c->local_anchor = raw;
    c->last_local = raw;
    c->last_master = master;
    c->leader = leader;
    c->term = term;
    c->synced = true;
    c->have_pair = true;
    c->samples++;
    return true;
}
