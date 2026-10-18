#ifndef LAB3_TIMING_STATS_H
#define LAB3_TIMING_STATS_H
#include <stdint.h>
enum lab3_timing_id {
    T_RX_DISPATCH=0, T_CAN_TX=1, T_STEER_DRIVE=2, T_HB_MON=3,
    T_HB_TX=4, T_PID=5, T_TEST_BTN=6, T_RELAY=7, T_COUNT=8
};
uint32_t lab3_timing_start(void);
void lab3_timing_end(enum lab3_timing_id id, uint32_t start_cycles);
uint32_t lab3_timing_max_us(enum lab3_timing_id id);
uint32_t lab3_timing_count(enum lab3_timing_id id);
#endif
