#include "pid_measurement.h"

void lab3_pid_measurement_init(struct lab3_pid_measurement *measurement)
{
    *measurement = (struct lab3_pid_measurement){0};
}

/* Bounded repeatable counts avoid signed overflow in a continuous bench run.
 * The returned result is consumed by firmware telemetry, preserving the work. */
struct lab3_pid_result lab3_pid_measurement_step(struct lab3_pid_measurement *measurement)
{
    static const int32_t count_steps[] = {44, 88, 132};
    static const float targets[] = {150.0f, 300.0f, 23.0f};
    unsigned sample = measurement->samples % 300;
    unsigned phase = sample / 100;
    if (sample == 0) {
        measurement->counts = 0;
        velocity_init(&measurement->control, 0, 0, 0);
    }
    if (sample == 200) {
        /* A fresh controller at high measured speed exercises its lower clamp. */
        velocity_init(&measurement->control, -measurement->counts,
            measurement->counts, (int64_t)sample * VELOCITY_PERIOD_MS);
    }
    measurement->counts += count_steps[phase];
    int status = velocity_update(&measurement->control, -measurement->counts,
        measurement->counts, (int64_t)(sample + 1) * VELOCITY_PERIOD_MS,
        targets[phase], true);
    measurement->samples++;
    return (struct lab3_pid_result){
        .samples = measurement->samples,
        .status = status,
        .rpm_milli = (int32_t)(measurement->control.average_rpm * 1000.0f),
        .duty_milli = (int32_t)(measurement->control.command[0] * 1000.0f),
    };
}
