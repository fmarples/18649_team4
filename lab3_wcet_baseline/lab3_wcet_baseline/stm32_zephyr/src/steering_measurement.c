#include "steering_measurement.h"
#include "servo_core.h"
#include "servo_calibration.h"

/* Same tracked calibration as Lab 2; no servo state machine or hardware driver. */
static const struct servo_control calibration = {
    .left = SERVO_DEFAULT_LEFT_US,
    .center = SERVO_DEFAULT_CENTER_US,
    .right = SERVO_DEFAULT_RIGHT_US,
    .marks = 7,
};

uint16_t lab3_steering_pulse(int16_t steer)
{
    return servo_map(&calibration, steer);
}
