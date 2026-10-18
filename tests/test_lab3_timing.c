/* Exercise the firmware's public timing API with known 84 MHz clock readings. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "timing_stats.h"
uint32_t test_cycles;
int main(void) {
    test_cycles = 100;
    uint32_t start = lab3_timing_start();
    test_cycles = 185; /* 85 cycles: just over one microsecond, must not report 1. */
    lab3_timing_end(T_HB_TX, start);
    assert(lab3_timing_max_us(T_HB_TX) == 2);
    assert(lab3_timing_count(T_HB_TX) == 1);
    /* A maximum cannot shrink; each activation still contributes to the count. */
    test_cycles = 200;
    start = lab3_timing_start();
    test_cycles = 242;
    lab3_timing_end(T_HB_TX, start);
    assert(lab3_timing_max_us(T_HB_TX) == 2);
    assert(lab3_timing_count(T_HB_TX) == 2);
    assert(lab3_timing_max_us(T_FORCE_TX) == 0);
    assert(lab3_timing_count(T_FORCE_TX) == 0);
    /* Counter rollover is unsigned subtraction, not a spurious huge duration. */
    test_cycles = UINT32_MAX - 41;
    start = lab3_timing_start();
    test_cycles = 42;
    lab3_timing_end(T_FORCE_TX, start);
    assert(lab3_timing_max_us(T_FORCE_TX) == 1);
    assert(lab3_timing_max_cycles(T_FORCE_TX) == 84);
    assert(lab3_timing_count(T_FORCE_TX) == 1);
    printf("OBS_TASK zone=N2 uptime_ms=5000 name=force_tx max_cycles=%u max_us=%u count=%u\n",
           lab3_timing_max_cycles(T_FORCE_TX), lab3_timing_max_us(T_FORCE_TX), lab3_timing_count(T_FORCE_TX));
    return 0;
}
