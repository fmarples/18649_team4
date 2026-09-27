#ifndef LAB_TIMING_TRACE_H
#define LAB_TIMING_TRACE_H
#include <stdint.h>
int timing_trace_init(void);
void timing_trace_command(void); /* Pi RX ISR: complete 28-byte candidate. */
void timing_trace_pwm(void);     /* Owner: final left motor timer write succeeded. */
uint32_t timing_trace_errors(void);
#endif
