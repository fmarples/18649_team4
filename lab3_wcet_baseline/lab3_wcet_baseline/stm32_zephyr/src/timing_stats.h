#ifndef LAB3_TIMING_STATS_H
#define LAB3_TIMING_STATS_H
#include <stdint.h>
enum lab3_timing_id {
    T_RX_DISPATCH=0, T_CAN_TX=1, T_STEER_DRIVE=2, T_HB_MON=3,
    T_HB_TX=4, T_PID=5, T_TEST_BTN=6, T_RELAY=7,
    T_FORCE_TX, T_BLINK, T_RX_DISPATCH_A, T_RX_DISPATCH_B,
    T_RX_QUEUE_A, T_RX_QUEUE_B, T_RX_CALLBACK_A, T_RX_CALLBACK_B,
    T_CONTROL_QUEUE, T_OVERHEAD, T_RX_CALLBACK_TO_END_A, T_RX_CALLBACK_TO_END_B, T_COUNT
};
const char *lab3_timing_name(enum lab3_timing_id id);
uint32_t lab3_timing_start(void);
void lab3_timing_end(enum lab3_timing_id id, uint32_t start_cycles);
/* Unsigned cycle subtraction supports one wrap; samples must be shorter than a wrap. */
uint32_t lab3_timing_max_cycles(enum lab3_timing_id id);
/* Round maxima upward, retaining raw cycles separately for analysis. */
uint32_t lab3_timing_max_us(enum lab3_timing_id id);
uint32_t lab3_timing_count(enum lab3_timing_id id);
#endif
