/* Runtime GPIO selection avoids reflashing for each task's scope measurement. */
#include "timing_probe.h"
#include "timing_trace.h"
#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include <zephyr/sys/atomic.h>
#include <errno.h>
#include <string.h>

#define TASK_PROBE 16
static atomic_t selected = -1;
static atomic_t ready;
static atomic_t tx_enabled = 1;

bool lab3_measurement_tx_enabled(void) {
    return atomic_get(&tx_enabled) != 0;
}

/* An aggregate RX selection follows either bus-specific dispatch marker. */
static bool probe_matches(enum lab3_timing_id id) {
    atomic_val_t probe = atomic_get(&selected);
    return probe == (atomic_val_t)id ||
        (probe == T_RX_DISPATCH && (id == T_RX_DISPATCH_A || id == T_RX_DISPATCH_B));
}

void lab3_probe_ready(void) {
    atomic_set(&ready, 1);
}

/* Only independently executing single-worker bodies can drive the shared probe. */
static bool probe_allowed(enum lab3_timing_id id) {
#if !defined(CONFIG_LAB3_ZONE_N3)
    if (id == T_PID) return false;
#endif
#if !defined(CONFIG_LAB3_ZONE_N2)
    if (id == T_FORCE_TX) return false;
#endif
#if !defined(CONFIG_LAB3_RELAY)
    if (id == T_RELAY) return false;
#endif
    return id == T_RX_DISPATCH || id == T_RX_DISPATCH_A || id == T_RX_DISPATCH_B ||
           id == T_STEER_DRIVE || id == T_HB_MON ||
           id == T_HB_TX || id == T_PID || id == T_TEST_BTN || id == T_RELAY ||
           id == T_FORCE_TX || id == T_BLINK;
}

uint32_t lab3_task_start(enum lab3_timing_id id) {
    if (probe_matches(id)) lab3_trace_set(TASK_PROBE, 1);
    return lab3_timing_start();
}

void lab3_task_end(enum lab3_timing_id id, uint32_t start) {
    lab3_timing_end(id, start);
    if (probe_matches(id)) lab3_trace_set(TASK_PROBE, 0);
}

/* `timing probe NAME|off` selects the PC8 pulse; queue delays cannot be selected. */
static int cmd_probe(const struct shell *shell, size_t argc, char **argv) {
    ARG_UNUSED(argc);
    if (!atomic_get(&ready)) {
        shell_error(shell, "Hardware initialization has not completed");
        return -EAGAIN;
    }
    int next = -1;
    if (strcmp(argv[1], "off") != 0) {
        for (int id=0; id<T_COUNT; ++id) {
            if (probe_allowed(id) && strcmp(argv[1], lab3_timing_name(id)) == 0) next = id;
        }
        if (next < 0) {
            shell_error(shell, "Select rx_dispatch, rx_dispatch_a/b, steer/drive (this zone), hb_mon, hb_tx, pid, test_btn, relay, force_tx, blink, or off");
            return -EINVAL;
        }
    }
    /* Changing selection interrupts the current pulse; discard that acquisition. */
    atomic_set(&selected, -1);
    lab3_trace_set(TASK_PROBE, 0);
    atomic_set(&selected, next);
    shell_print(shell, "PC8 probe=%s; discard captures during selection changes", argv[1]);
    return 0;
}

/* Pause application submissions only; already queued CAN frames may still finish. */
static int cmd_tx(const struct shell *shell, size_t argc, char **argv) {
    ARG_UNUSED(argc);
    if (!atomic_get(&ready)) return -EAGAIN;
    if (strcmp(argv[1], "on") != 0 && strcmp(argv[1], "off") != 0) return -EINVAL;
    atomic_set(&tx_enabled, strcmp(argv[1], "on") == 0);
    shell_print(shell, "Application TX=%s; queued frames may still finish", argv[1]);
    return 0;
}

SHELL_STATIC_SUBCMD_SET_CREATE(timing_commands,
    SHELL_CMD_ARG(probe, NULL, "Select one task's PC8 elapsed-body pulse, or off", cmd_probe, 2, 0),
    SHELL_CMD_ARG(tx, NULL, "Application TX on/off for isolated receive measurements", cmd_tx, 2, 0),
    SHELL_SUBCMD_SET_END);
SHELL_CMD_REGISTER(timing, &timing_commands, "Measurement controls", NULL);
