#ifndef SERVO_BENCH_H
#define SERVO_BENCH_H
#include <stdbool.h>
#include <stdint.h>
#include "servo_core.h"
int servo_bench_init(void);
/* USB replies are printed only by the diagnostic thread, never the motor owner. */
void servo_bench_print_replies(void);
void servo_bench_off(void);
int servo_bench_service(bool linked, bool self_test, int32_t steer);
/* Owner-thread-only snapshot; publish under state_mutex for diagnostic readers. */
struct servo_control servo_bench_snapshot(void);
#endif
