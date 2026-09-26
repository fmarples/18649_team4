#ifndef BENCH_CONTROL_H
#define BENCH_CONTROL_H

#include <stdbool.h>
#include <stdint.h>

/* Explicitly armed forward trial; changing limits requires rebuild/reflash. */
#ifndef BENCH_DUTY_PERCENT
#define BENCH_DUTY_PERCENT 60U
#endif
_Static_assert(BENCH_DUTY_PERCENT >= 1 && BENCH_DUTY_PERCENT <= 100,
               "Bench duty must be 1..100 percent");
#define BENCH_PULSE_MS 200
/* Hold commands always start with a 60% kick; each enabled wheel is guarded. */
#define BENCH_KICK_PERCENT 60U
#ifndef BENCH_HOLD_MS
#define BENCH_HOLD_MS 2000
#endif
_Static_assert(BENCH_HOLD_MS == 2000 || BENCH_HOLD_MS == 4000,
               "Hold duration must be 2000 or 4000 ms");
#ifndef BENCH_HOLD_PERCENT
#define BENCH_HOLD_PERCENT 55U
#endif
_Static_assert(BENCH_HOLD_PERCENT >= 1 && BENCH_HOLD_PERCENT <= 60,
               "Hold duty must be 1..60 percent");
#define BENCH_STALL_MS 150
#define BENCH_PROGRESS_COUNTS 4

/* Isolated bench protocol, NOT the Pi/STM32 Part 2 protocol. */
enum bench_phase { BENCH_IDLE, BENCH_ARMED, BENCH_LEFT, BENCH_RIGHT, BENCH_BOTH };
enum bench_fault {
    BENCH_OK, BENCH_LEFT_STALL, BENCH_RIGHT_STALL,
    BENCH_LEFT_REVERSED, BENCH_RIGHT_REVERSED
};
struct bench_control {
    enum bench_phase phase;
    enum bench_fault fault;
    int64_t deadline_ms;
    bool hold_test;
    int64_t hold_at_ms;
    int32_t counts[2];
    int32_t anchors[2];
    int64_t progress_ms[2];
};
struct bench_output {
    unsigned left_percent;
    unsigned right_percent;
};

/* Boot/reset only. STOP does not clear a latched motion fault. */
void bench_init(struct bench_control *control);
/* Raw calibrated counts: left must decrease forward, right must increase. */
void bench_encoder_update(struct bench_control *control, int32_t left,
                          int32_t right, int64_t now_ms);
bool bench_command(struct bench_control *control, const char *command, int64_t now_ms);
struct bench_output bench_tick(struct bench_control *control, int64_t now_ms);

#endif
