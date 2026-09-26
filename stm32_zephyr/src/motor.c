#include "motor.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>

/* TODO: Replace these DT aliases with the pins/PWM outputs used by your H-bridge. */
#define PWM_PERIOD_NS 20000000U

static const struct pwm_dt_spec left_pwm = PWM_DT_SPEC_GET(DT_ALIAS(motor_left_pwm));
static const struct pwm_dt_spec right_pwm = PWM_DT_SPEC_GET(DT_ALIAS(motor_right_pwm));
static const struct gpio_dt_spec dir_a = GPIO_DT_SPEC_GET(DT_ALIAS(motor_dir_a), gpios);
static const struct gpio_dt_spec dir_b = GPIO_DT_SPEC_GET(DT_ALIAS(motor_dir_b), gpios);

void motor_init(void) {
    /* TODO: check all devices with device_is_ready() and configure GPIOs. */
    gpio_pin_configure_dt(&dir_a, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure_dt(&dir_b, GPIO_OUTPUT_INACTIVE);
    motor_disable();
}

void motor_set_direction(bool forward) {
    gpio_pin_set_dt(&dir_a, forward ? 1 : 0);
    gpio_pin_set_dt(&dir_b, forward ? 0 : 1);
}

void motor_set_pwm(uint8_t left_percent, uint8_t right_percent) {
    if (left_percent > 100) left_percent = 100;
    if (right_percent > 100) right_percent = 100;
    pwm_set_dt(&left_pwm, PWM_PERIOD_NS, (PWM_PERIOD_NS * left_percent) / 100U);
    pwm_set_dt(&right_pwm, PWM_PERIOD_NS, (PWM_PERIOD_NS * right_percent) / 100U);
}

void motor_disable(void) {
    pwm_set_dt(&left_pwm, PWM_PERIOD_NS, 0);
    pwm_set_dt(&right_pwm, PWM_PERIOD_NS, 0);
}

void motor_dynamic_brake(void) {
    /* TODO: Verify your H-bridge's actual dynamic-braking truth table.
     * Do NOT assume these GPIO states are correct for your driver. */
    motor_disable();
    gpio_pin_set_dt(&dir_a, 1);
    gpio_pin_set_dt(&dir_b, 1);
}
