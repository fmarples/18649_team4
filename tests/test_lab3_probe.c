/* Test the registered probe command and GPIO/counter behavior through public interfaces. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <zephyr/shell/shell.h>
#include "timing_probe.h"
#include "timing_trace.h"

extern const struct test_command *test_shell_timing;
uint32_t test_cycles;
static int probe_level;
static unsigned writes;

/* Test GPIO sink records the same trace API used by the target. */
void lab3_trace_set(unsigned pin, int active) {
    assert(pin == 16);
    probe_level = active;
    ++writes;
}

static int select_probe(char *name) {
    char *argv[] = {"probe", name};
    return test_shell_timing[0].handler(NULL, 2, argv);
}

int main(void) {
    assert(select_probe("hb_tx") == -EAGAIN);
    assert(writes == 0);
    lab3_probe_ready();
    assert(select_probe("hb_tx") == 0);
    assert(probe_level == 0);
    test_cycles = 100;
    uint32_t start = lab3_task_start(T_HB_TX);
    assert(probe_level == 1);
    test_cycles = 184;
    lab3_task_end(T_HB_TX, start);
    assert(probe_level == 0);
    assert(lab3_timing_count(T_HB_TX) == 1);
    assert(lab3_timing_max_us(T_HB_TX) == 1);
    assert(select_probe("rx_queue_a") == -EINVAL);
    assert(select_probe("relay") == -EINVAL); /* Disabled in default measurement build. */
#if defined(CONFIG_LAB3_ZONE_N2)
    assert(select_probe("pid") == -EINVAL);
    assert(select_probe("steer") == 0);
#else
    assert(select_probe("force_tx") == -EINVAL);
    assert(select_probe("drive") == 0);
#endif
    assert(select_probe("rx_dispatch_a") == 0);
    start = lab3_task_start(T_RX_DISPATCH_B);
    assert(probe_level == 0);
    lab3_task_end(T_RX_DISPATCH_B, start);
    start = lab3_task_start(T_RX_DISPATCH_A);
    assert(probe_level == 1);
    lab3_task_end(T_RX_DISPATCH_A, start);
    assert(probe_level == 0);
    assert(select_probe("rx_dispatch") == 0);
    start = lab3_task_start(T_RX_DISPATCH_B);
    assert(probe_level == 1);
    lab3_task_end(T_RX_DISPATCH_B, start);
#if defined(CONFIG_LAB3_ZONE_N2)
    assert(select_probe("steer") == 0);
#else
    assert(select_probe("drive") == 0);
#endif
    start = lab3_task_start(T_HB_TX);
    assert(probe_level == 0); /* Unselected tasks still update their counters. */
    lab3_task_end(T_HB_TX, start);
    assert(lab3_timing_count(T_HB_TX) == 2);
    start = lab3_task_start(T_STEER_DRIVE);
    assert(probe_level == 1);
    assert(select_probe("off") == 0);
    assert(probe_level == 0);
    lab3_task_end(T_STEER_DRIVE, start);
    assert(probe_level == 0);
    assert(lab3_measurement_tx_enabled());
    char *off[] = {"tx", "off"};
    char *on[] = {"tx", "on"};
    char *invalid[] = {"tx", "invalid"};
    assert(test_shell_timing[1].handler(NULL, 2, off) == 0);
    assert(!lab3_measurement_tx_enabled());
    assert(test_shell_timing[1].handler(NULL, 2, invalid) == -EINVAL);
    assert(!lab3_measurement_tx_enabled());
    assert(test_shell_timing[1].handler(NULL, 2, on) == 0);
    assert(lab3_measurement_tx_enabled());
    return 0;
}
