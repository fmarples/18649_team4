/* Low-overhead observed execution timing; max is not a formal WCET proof. */
#include "timing_stats.h"
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
static atomic_t max_cycles[T_COUNT];
static atomic_t counts[T_COUNT];
static const char *const names[T_COUNT] = {
    "rx_dispatch", "can_tx",
#if defined(CONFIG_LAB3_ZONE_N2)
    "steer",
#else
    "drive",
#endif
    "hb_mon", "hb_tx", "pid", "test_btn", "relay", "force_tx", "blink",
    "rx_dispatch_a", "rx_dispatch_b", "rx_queue_a", "rx_queue_b",
    "rx_callback_a", "rx_callback_b", "control_queue", "overhead",
    "rx_callback_to_end_a", "rx_callback_to_end_b",
};

/* Names are shared by console records and the runtime GPIO probe selector. */
const char *lab3_timing_name(enum lab3_timing_id id) {
    return id >= 0 && id < T_COUNT ? names[id] : 0;
}
uint32_t lab3_timing_start(void) { return k_cycle_get_32(); }
void lab3_timing_end(enum lab3_timing_id id, uint32_t start) {
    if (id < 0 || id >= T_COUNT) return;
    uint32_t elapsed = k_cycle_get_32() - start;
    atomic_inc(&counts[id]);
    atomic_val_t old = atomic_get(&max_cycles[id]);
    while ((uint32_t)old < elapsed && !atomic_cas(&max_cycles[id], old, (atomic_val_t)elapsed))
        old = atomic_get(&max_cycles[id]);
}
/* Preserve raw maxima so integer microsecond rounding is visible in reports. */
uint32_t lab3_timing_max_cycles(enum lab3_timing_id id) {
    if (id < 0 || id >= T_COUNT) return 0;
    return (uint32_t)atomic_get(&max_cycles[id]);
}
uint32_t lab3_timing_max_us(enum lab3_timing_id id) {
    return k_cyc_to_us_ceil32(lab3_timing_max_cycles(id));
}
uint32_t lab3_timing_count(enum lab3_timing_id id) {
    if (id < 0 || id >= T_COUNT) return 0;
    return (uint32_t)atomic_get(&counts[id]);
}
