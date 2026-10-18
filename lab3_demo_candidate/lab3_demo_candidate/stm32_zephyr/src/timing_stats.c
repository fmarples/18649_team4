/* Low-overhead observed execution timing; max is not a formal WCET proof. */
#include "timing_stats.h"
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
static atomic_t max_cycles[T_COUNT];
static atomic_t counts[T_COUNT];
uint32_t lab3_timing_start(void) { return k_cycle_get_32(); }
void lab3_timing_end(enum lab3_timing_id id, uint32_t start) {
    if (id < 0 || id >= T_COUNT) return;
    uint32_t elapsed = k_cycle_get_32() - start;
    atomic_inc(&counts[id]);
    atomic_val_t old = atomic_get(&max_cycles[id]);
    while ((uint32_t)old < elapsed && !atomic_cas(&max_cycles[id], old, (atomic_val_t)elapsed))
        old = atomic_get(&max_cycles[id]);
}
uint32_t lab3_timing_max_us(enum lab3_timing_id id) {
    if (id < 0 || id >= T_COUNT) return 0;
    return k_cyc_to_us_floor32((uint32_t)atomic_get(&max_cycles[id]));
}
uint32_t lab3_timing_count(enum lab3_timing_id id) {
    if (id < 0 || id >= T_COUNT) return 0;
    return (uint32_t)atomic_get(&counts[id]);
}
