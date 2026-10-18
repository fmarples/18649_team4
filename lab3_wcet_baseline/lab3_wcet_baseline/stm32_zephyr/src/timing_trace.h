#ifndef LAB3_TIMING_TRACE_H
#define LAB3_TIMING_TRACE_H
#include <stdint.h>
int lab3_trace_init(void);
void lab3_trace_toggle(unsigned index);
void lab3_trace_set(unsigned index, int active);
/* Probe indexes: 0 RX_A, 1 RX_B, 2 TX_A, 3 TX_B, 4 DEG_A, 5 DEG_B,
 * 6 ERR, 7 SRV/STEER, 8 PWM_SET/DRIVE, 9 DIR_A, 10 PID, 11 FL, 12 FR, 13 RL, 14 RR, 15 RELAY_TX. */
#endif
