#ifndef LAB3_TIMING_TRACE_H
#define LAB3_TIMING_TRACE_H
#include <stdint.h>
/* Same API and index layout as the baseline's timing_trace.h, because the reused
 * baseline timing_probe.c drives index 16. Pins: boards/nucleo_f401re.overlay. */
enum lab3_test_point {
    TP_CAN_RX_A, TP_CAN_RX_B, TP_CAN_TX_A, TP_CAN_TX_B, TP_DEG_A, TP_DEG_B,
    TP_ERR, TP_STEER, TP_PWM_SET, TP_DIR_A, TP_PID, TP_FL, TP_FR, TP_RL, TP_RR,
    TP_RELAY_TX, TP_TASK_PROBE,
};
int lab3_trace_init(void);
void lab3_trace_toggle(unsigned index);
void lab3_trace_set(unsigned index, int active);
#endif
