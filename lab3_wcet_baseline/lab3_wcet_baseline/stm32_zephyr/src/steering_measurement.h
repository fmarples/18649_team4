#ifndef LAB3_STEERING_MEASUREMENT_H
#define LAB3_STEERING_MEASUREMENT_H
#include <stdint.h>
/* Run Lab 2's calibrated mapping only; the returned microseconds never drive PWM. */
uint16_t lab3_steering_pulse(int16_t steer);
#endif
