#ifndef LAB3_TIMING_PROBE_H
#define LAB3_TIMING_PROBE_H
#include "timing_stats.h"
#include <stdbool.h>
/* Measurement-only TX gate, default on; pause both nodes for isolated RX captures. */
bool lab3_measurement_tx_enabled(void);
/* Called by main only after hardware initialization succeeds. */
void lab3_probe_ready(void);
/* The selected single-worker task pulses PC8; all bodies retain cycle statistics. */
uint32_t lab3_task_start(enum lab3_timing_id id);
void lab3_task_end(enum lab3_timing_id id, uint32_t start);
#endif
