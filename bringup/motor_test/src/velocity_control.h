#ifndef VELOCITY_CONTROL_H
#define VELOCITY_CONTROL_H

#include <stdbool.h>
#include <stdint.h>

#define VELOCITY_COUNTS_PER_REV 1320.0f
#define VELOCITY_PERIOD_MS 20
/* User retains measured 40% sustaining floor and existing 60% startup kick. */
#define VELOCITY_START_DUTY 60U
#define VELOCITY_RUN_MIN_DUTY 40.0f
#define VELOCITY_MAX_DUTY 100.0f
#define VELOCITY_KP 0.12f
#define VELOCITY_KI 0.35f
#define VELOCITY_KD 0.003f
#define VELOCITY_FILTER_SECONDS 0.06f

/* One plain PID on average forward RPM; same output drives both wheels.
 * State is owned by the motor-control thread, copied only for telemetry. */
struct velocity_control {
    int64_t sample_ms;
    int32_t previous_counts[2];
    bool measured;
    bool regulating;
    float rpm[2];
    float average_rpm;
    float command[2];
    float p_term;
    float i_term;
    float d_term;
};

/* Reset only on a new armed trial or stop; repeated samples retain PID history. */
void velocity_init(struct velocity_control *control, int32_t left, int32_t right,
                   int64_t now_ms);
/* Raw counts use left-negative/right-positive forward signs. During the startup
 * kick, regulate=false updates speed but freezes PID history. Returns -1 and
 * zero commands for invalid target/time/data. The caller must latch a stop.
 * Calls less than 20 ms apart retain the latest output; longer intervals use
 * their actual elapsed time. The caller implements zero-target STOP. */
int velocity_update(struct velocity_control *control, int32_t left, int32_t right,
                    int64_t now_ms, float target_rpm, bool regulate);

#endif
