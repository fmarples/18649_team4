#include "current_sensor.h"
#include <zephyr/drivers/adc.h>

/* TODO: Replace ADC aliases/channels and conversion constants with your sensor data sheet. */
static const struct adc_dt_spec motor_left = ADC_DT_SPEC_GET(DT_ALIAS(current_motor_left));
static const struct adc_dt_spec motor_right = ADC_DT_SPEC_GET(DT_ALIAS(current_motor_right));
static const struct adc_dt_spec servo = ADC_DT_SPEC_GET(DT_ALIAS(current_servo));

static uint16_t read_ma(const struct adc_dt_spec *s) {
    int16_t raw;
    struct adc_sequence seq = { .buffer = &raw, .buffer_size = sizeof(raw) };
    int rc = adc_sequence_init_dt(s, &seq);
    if (rc) return 0;
    rc = adc_read_dt(s, &seq);
    if (rc) return 0;
    /* TODO: Convert raw ADC units to mA using your current sensor's transfer function. */
    return (uint16_t)raw;
}
void current_sensor_init(void) {
    /* TODO: call adc_channel_setup_dt() for each channel and check readiness. */
}
uint16_t current_motor_left_ma(void) { return read_ma(&motor_left); }
uint16_t current_motor_right_ma(void) { return read_ma(&motor_right); }
uint16_t current_servo_ma(void) { return read_ma(&servo); }
