#include "motor_driver.h"
#include "bench_encoders.h"
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>

static const struct pwm_dt_spec pwms[] = {
    PWM_DT_SPEC_GET(DT_NODELABEL(left_pwm)), PWM_DT_SPEC_GET(DT_NODELABEL(right_pwm)),
};
static const struct gpio_dt_spec directions[] = {
    GPIO_DT_SPEC_GET(DT_NODELABEL(in1), gpios), GPIO_DT_SPEC_GET(DT_NODELABEL(in2), gpios),
    GPIO_DT_SPEC_GET(DT_NODELABEL(in3), gpios), GPIO_DT_SPEC_GET(DT_NODELABEL(in4), gpios),
};
static const struct gpio_dt_spec enables[] = {
    GPIO_DT_SPEC_GET(DT_NODELABEL(ena), gpios), GPIO_DT_SPEC_GET(DT_NODELABEL(enb), gpios),
};
static const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);
static struct gpio_callback button_callback;
static atomic_t button_latched;
static int hardware_fault;
static struct drive_control control;
static struct drive_output applied;

/* Preserve a short B1 press independently of host traffic and later release. */
static void on_button(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    ARG_UNUSED(dev); ARG_UNUSED(cb); ARG_UNUSED(pins);
    atomic_set(&button_latched, 1);
}

/* A failed HAL cannot be trusted to brake. Reclaim enables as GPIO-low and
 * keep the fault latched; no later command may restore their PWM pinctrl. */
static int force_off(void)
{
    int error = 0;
    for (size_t i = 0; i < ARRAY_SIZE(enables); ++i) {
        int ret = gpio_pin_configure_dt(&enables[i], GPIO_OUTPUT_INACTIVE);
        if (ret < 0 && !error) { error = ret; }
    }
    for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
        int ret = gpio_pin_configure_dt(&directions[i], GPIO_OUTPUT_INACTIVE);
        if (ret < 0 && !error) { error = ret; }
    }
    return error;
}

/* ST L298 DS0218 Rev 5 Table 5: enabled + equal INs is fast stop;
 * enable-low is coast. BRAKE uses steady enable high, not propulsive PWM.
 * Keep forward polarity from the verified bench: left 01, right 10. */
static int apply_output(struct drive_output output)
{
    if (output.mode != applied.mode) {
        for (size_t i = 0; i < ARRAY_SIZE(pwms); ++i) {
            int ret = pwm_set_dt(&pwms[i], pwms[i].period, 0);
            if (ret < 0) { return ret; }
        }
        k_busy_wait(100); /* One 10 kHz PWM period before changing direction. */
        int in[] = {0, output.mode == DRIVE_FORWARD, output.mode == DRIVE_FORWARD, 0};
        for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
            int ret = gpio_pin_set_dt(&directions[i], in[i]);
            if (ret < 0) { return ret; }
        }
    }
    for (size_t i = 0; i < ARRAY_SIZE(pwms); ++i) {
        uint32_t pulse = output.mode == DRIVE_BRAKE ? pwms[i].period :
            output.mode == DRIVE_FORWARD ? (uint32_t)(pwms[i].period * output.duty_percent / 100.0f) : 0;
        int ret = pwm_set_dt(&pwms[i], pwms[i].period, pulse);
        if (ret < 0) { return ret; }
    }
    applied = output;
    return 0;
}

/* Hardware setup is complete before the first link command can drive. */
static int configure_hardware(void)
{
    for (size_t i = 0; i < ARRAY_SIZE(pwms); ++i) {
        if (!pwm_is_ready_dt(&pwms[i]) || !gpio_is_ready_dt(&enables[i])) { return -ENODEV; }
        int ret = pwm_set_dt(&pwms[i], pwms[i].period, 0);
        if (ret < 0) { return ret; }
    }
    for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
        if (!gpio_is_ready_dt(&directions[i])) { return -ENODEV; }
        int ret = gpio_pin_configure_dt(&directions[i], GPIO_OUTPUT_INACTIVE);
        if (ret < 0) { return ret; }
    }
    if (!gpio_is_ready_dt(&button)) { return -ENODEV; }
    int ret = gpio_pin_configure_dt(&button, GPIO_INPUT | GPIO_PULL_UP);
    if (ret < 0) { return ret; }
    gpio_init_callback(&button_callback, on_button, BIT(button.pin));
    ret = gpio_add_callback(button.port, &button_callback);
    if (ret < 0) { return ret; }
    ret = gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_TO_ACTIVE);
    if (ret < 0) { return ret; }
    return bench_encoders_init();
}

int motor_init(void)
{
    drive_init(&control);
    int ret = configure_hardware();
    if (ret < 0) {
        int off_ret = force_off();
        hardware_fault = off_ret < 0 ? off_ret : ret;
    }
    return hardware_fault;
}

/* Saturate only the telemetry integer representation, not control or speed. */
static int32_t milli_rpm(float rpm)
{
    double scaled = (double)rpm * 1000.0;
    if (!isfinite(scaled)) { return INT32_MIN; }
    if (scaled >= INT32_MAX) { return INT32_MAX; }
    if (scaled <= INT32_MIN) { return INT32_MIN; }
    return (int32_t)scaled;
}

struct motor_report motor_update(struct drive_input input)
{
    struct bench_encoder_sample sample = {0};
    if (!hardware_fault) {
        int pressed = gpio_pin_get_dt(&button);
        int ret = bench_encoders_read(&sample);
        if (pressed < 0 || ret < 0 || sample.invalid[0] || sample.invalid[1]) {
            input.sensor_fault = true;
        }
        if (pressed > 0) { atomic_set(&button_latched, 1); }
        input.local_stop = atomic_get(&button_latched) != 0;
        struct drive_output output = drive_step(&control, input, sample.counts[0],
                                                sample.counts[1], sample.time_ms);
        if (output.mode != applied.mode || output.duty_percent != applied.duty_percent) {
            ret = apply_output(output);
            /* An IRQ during GPIO/PWM work must not leave propulsion enabled. */
            if (ret >= 0 && atomic_get(&button_latched) && control.fault == DRIVE_OK) {
                input.local_stop = true;
                output = drive_step(&control, input, sample.counts[0], sample.counts[1], sample.time_ms);
                ret = apply_output(output);
            }
            if (ret < 0) {
                int off_ret = force_off();
                hardware_fault = off_ret < 0 ? off_ret : ret;
                applied = (struct drive_output){DRIVE_COAST, 0};
            }
        }
    }
    return (struct motor_report){
        .fault = hardware_fault ? hardware_fault : (int)control.fault,
        .mode = applied.mode,
        .target_mrpm = hardware_fault ? 0 : control.target_mrpm,
        .left_mrpm = milli_rpm(control.velocity.rpm[0]),
        .right_mrpm = milli_rpm(control.velocity.rpm[1]),
        .average_mrpm = milli_rpm(control.velocity.average_rpm),
        .duty_mpercent = (uint32_t)(applied.duty_percent * 1000.0f),
        .left_count = sample.counts[0], .right_count = sample.counts[1],
        .sample_ms = sample.time_ms,
    };
}
