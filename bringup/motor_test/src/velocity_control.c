#include "velocity_control.h"
#include <math.h>

void velocity_init(struct velocity_control *control, int32_t left, int32_t right,
                   int64_t now_ms)
{
    /* Start the integral at the existing kick duty to avoid dropping to zero
     * when the controller takes over. Subsequent output is just P + I + D. */
    *control = (struct velocity_control){
        .sample_ms = now_ms, .previous_counts = {left, right},
        .i_term = VELOCITY_START_DUTY,
    };
}

int velocity_update(struct velocity_control *control, int32_t left, int32_t right,
                    int64_t now_ms, float target_rpm, bool regulate)
{
    int64_t elapsed = now_ms - control->sample_ms;
    if (!isfinite(target_rpm) || target_rpm <= 0 || elapsed < 0) {
        control->command[0] = control->command[1] = 0;
        return -1;
    }
    if (elapsed < VELOCITY_PERIOD_MS) { return 0; }
    float dt = (float)elapsed / 1000.0f;
    float previous_average = control->average_rpm;
    int32_t counts[] = {left, right};
    for (unsigned i = 0; i < 2; ++i) {
        int64_t delta = (int64_t)counts[i] - control->previous_counts[i];
        float raw_rpm = (float)(i == 0 ? -delta : delta) * 60.0f /
                        (VELOCITY_COUNTS_PER_REV * dt);
        if (!isfinite(raw_rpm)) {
            control->command[0] = control->command[1] = 0;
            return -1;
        }
        control->rpm[i] = control->measured ? control->rpm[i] +
            dt / (VELOCITY_FILTER_SECONDS + dt) * (raw_rpm - control->rpm[i]) : raw_rpm;
        control->previous_counts[i] = counts[i];
    }
    control->sample_ms = now_ms;
    control->measured = true;
    control->average_rpm = (control->rpm[0] + control->rpm[1]) * 0.5f;
    if (!regulate) {
        control->regulating = false;
        control->p_term = control->d_term = 0;
        control->command[0] = control->command[1] = 0;
        return 0;
    }
    float error = target_rpm - control->average_rpm;
    control->p_term = VELOCITY_KP * error;
    control->d_term = control->regulating ?
        -VELOCITY_KD * (control->average_rpm - previous_average) / dt : 0;
    float candidate_i = control->i_term + VELOCITY_KI * error * dt;
    float candidate = control->p_term + candidate_i + control->d_term;
    /* Anti-windup follows the user-selected sustaining floor and physical PWM
     * range. There is no separate arbitrary integral limit. */
    if (!((candidate > VELOCITY_MAX_DUTY && error > 0) ||
          (candidate < VELOCITY_RUN_MIN_DUTY && error < 0))) {
        control->i_term = candidate_i;
    }
    float output = control->p_term + control->i_term + control->d_term;
    if (output < VELOCITY_RUN_MIN_DUTY) { output = VELOCITY_RUN_MIN_DUTY; }
    if (output > VELOCITY_MAX_DUTY) { output = VELOCITY_MAX_DUTY; }
    control->regulating = true;
    control->command[0] = control->command[1] = output;
    return 0;
}
