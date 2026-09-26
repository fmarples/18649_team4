#include "steering.h"
#include <zephyr/drivers/pwm.h>

/* TODO: Change DT alias and calibration values after measuring your servo/chassis. */
static const struct pwm_dt_spec servo = PWM_DT_SPEC_GET(DT_ALIAS(steering_servo));
#define SERVO_PERIOD_NS 20000000U
#define WHEEL_MIN (-360)
#define WHEEL_MAX 360
#define SERVO_MIN_US 1000
#define SERVO_MAX_US 2000

static int clamp(int x, int lo, int hi) { return x < lo ? lo : (x > hi ? hi : x); }

void steering_init(void) {
    /* TODO: verify servo PWM frequency and endpoint pulse widths. */
}

void steering_set_from_wheel(int16_t wheel_value) {
    int x = clamp(wheel_value, WHEEL_MIN, WHEEL_MAX);
    int us = SERVO_MIN_US + ((x - WHEEL_MIN) * (SERVO_MAX_US - SERVO_MIN_US)) /
             (WHEEL_MAX - WHEEL_MIN);
    pwm_set_dt(&servo, SERVO_PERIOD_NS, (uint32_t)us * 1000U);
}
