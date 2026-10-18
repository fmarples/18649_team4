#ifndef LAB3_PID_MEASUREMENT_H
#define LAB3_PID_MEASUREMENT_H
#include "velocity_control.h"

struct lab3_pid_measurement {
    struct velocity_control control;
    uint32_t samples;
    int32_t counts;
};

struct lab3_pid_result {
    uint32_t samples;
    int status;
    int32_t rpm_milli;
    int32_t duty_milli;
};

/* Synthetic benchmark only: no encoder, PWM or motor-driver access. */
void lab3_pid_measurement_init(struct lab3_pid_measurement *measurement);
/* Run one full, unchanged Lab 2 PID update on a synthetic 20 ms encoder sample.
 * The Lab 3 worker invokes this every 10 ms; synthetic time is independent.
 * Three 100-sample phases exercise under-speed, acceleration and overspeed. */
struct lab3_pid_result lab3_pid_measurement_step(struct lab3_pid_measurement *measurement);
#endif
