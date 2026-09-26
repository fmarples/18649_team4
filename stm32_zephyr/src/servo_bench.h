#ifndef SERVO_BENCH_H
#define SERVO_BENCH_H
#include <stdbool.h>
#include <stdint.h>
int servo_bench_init(void);
void servo_bench_off(void);
int servo_bench_service(bool linked, bool self_test, int32_t steer);
#endif
