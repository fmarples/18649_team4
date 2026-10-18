/* Host-only clock seam for the real firmware timing accumulator tests. */
#ifndef TEST_LAB3_KERNEL_H
#define TEST_LAB3_KERNEL_H
#include <stdint.h>
#define ARG_UNUSED(value) (void)(value)
extern uint32_t test_cycles;
static inline uint32_t k_cycle_get_32(void) { return test_cycles; }
static inline uint32_t k_cyc_to_us_floor32(uint32_t cycles) { return cycles / 84U; }
static inline uint32_t k_cyc_to_us_ceil32(uint32_t cycles) {
    return (uint32_t)(((uint64_t)cycles + 83U) / 84U);
}
#endif
