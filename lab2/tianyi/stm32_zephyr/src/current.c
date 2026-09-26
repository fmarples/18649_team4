#include "current.h"

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/sys/util.h>
#include <stdint.h>

/*
 * User pinout:
 * motor current #1 = PA0 / ADC1_IN0
 * motor current #2 = PA1 / ADC1_IN1
 * servo current     = PB0 / ADC1_IN8
 *
 * The actual current-sensor transfer function was not provided in the lab
 * source. These constants are therefore calibration parameters, not claims
 * about the sensor hardware.
 *
 * Set:
 *   CURRENT_ZERO_MV
 *   CURRENT_MV_PER_AMP
 * after measuring the actual sensors.
 */
#define CURRENT_ZERO_MV     0.0f
#define CURRENT_MV_PER_AMP  1000.0f

#define CURRENT_RESOLUTION 12
#define ADC_VREF_MV 3300

static const struct adc_dt_spec left_adc =
	ADC_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), left_motor_current);

static const struct adc_dt_spec right_adc =
	ADC_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), right_motor_current);

static const struct adc_dt_spec servo_adc =
	ADC_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), servo_current);

static int16_t sample_buf;

static int sample_one(const struct adc_dt_spec *adc, int32_t *mA)
{
	struct adc_sequence sequence = {
		.buffer = &sample_buf,
		.buffer_size = sizeof(sample_buf),
	};

	int rc = adc_sequence_init_dt(adc, &sequence);
	if (rc)
		return rc;

	rc = adc_read(adc->dev, &sequence);
	if (rc)
		return rc;

	int32_t raw = sample_buf;

	/*
	 * Convert 12-bit ADC code to input voltage, then use the configured
	 * sensor transfer function.
	 */
	float mv = ((float)raw * ADC_VREF_MV) / 4095.0f;
	float amps = (mv - CURRENT_ZERO_MV) / CURRENT_MV_PER_AMP;

	*mA = (int32_t)(amps * 1000.0f);
	return 0;
}

int current_init(void)
{
	if (!device_is_ready(left_adc.dev) ||
	    !device_is_ready(right_adc.dev) ||
	    !device_is_ready(servo_adc.dev))
		return -ENODEV;

	int rc;
	rc = adc_channel_setup_dt(&left_adc);
	if (rc) return rc;
	rc = adc_channel_setup_dt(&right_adc);
	if (rc) return rc;
	rc = adc_channel_setup_dt(&servo_adc);
	if (rc) return rc;

	return 0;
}

int current_get_mA(int32_t *left_mA,
                   int32_t *right_mA,
                   int32_t *servo_mA,
                   uint32_t *valid_mask)
{
	uint32_t mask = 0;

	*left_mA = INT32_MIN;
	*right_mA = INT32_MIN;
	*servo_mA = INT32_MIN;

	if (sample_one(&left_adc, left_mA) == 0)
		mask |= BIT(0);

	if (sample_one(&right_adc, right_mA) == 0)
		mask |= BIT(1);

	if (sample_one(&servo_adc, servo_mA) == 0)
		mask |= BIT(2);

	*valid_mask = mask;
	return 0;
}
