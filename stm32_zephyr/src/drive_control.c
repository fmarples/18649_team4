#include "drive_control.h"
#include "motor.h"
#include "encoder.h"
#include "pid.h"

/* TODO: Replace these with your documented team-defined mapping/calibration. */
#define THROTTLE_MIN 0
#define THROTTLE_MAX 100
#define MAX_VELOCITY_MPS 1.0f
#define BRAKE_THRESHOLD 1

static pid_t left_pid;
static pid_t right_pid;

static float throttle_to_velocity(int16_t throttle) {
    if (throttle < THROTTLE_MIN) throttle = THROTTLE_MIN;
    if (throttle > THROTTLE_MAX) throttle = THROTTLE_MAX;
    return ((float)throttle / 100.0f) * MAX_VELOCITY_MPS;
}

void drive_control_init(void) {
    motor_init();
    encoder_init();
    /* TODO: Tune these gains experimentally. Do not treat them as final values. */
    pid_init(&left_pid, 10.0f, 0.5f, 0.0f);
    pid_init(&right_pid, 10.0f, 0.5f, 0.0f);
}

void drive_control_step(int16_t throttle, int16_t brake, int error_state) {
    /* Brake and error state always override throttle. */
    if (error_state || brake > BRAKE_THRESHOLD) {
        motor_dynamic_brake();
        return;
    }

    float target = throttle_to_velocity(throttle);
    float measured = encoder_get_average_velocity_mps();
    float control = pid_update(&left_pid, target, measured, 0.002f);
    float right_control = pid_update(&right_pid, target, measured, 0.002f);

    if (control < 0) control = 0;
    if (right_control < 0) right_control = 0;
    if (control > 100) control = 100;
    if (right_control > 100) right_control = 100;

    motor_set_direction(true);
    motor_set_pwm((uint8_t)control, (uint8_t)right_control);
}
