#include "servo.h"

#include <zephyr/device.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/sys/util.h>

static const struct pwm_dt_spec servo_pwm =
	PWM_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), steering_servo_pwm);

/* Hiwonder-style servo: 20 ms period, approximately 500-2500 us. */
#define SERVO_PERIOD_NS 20000000U
#define SERVO_MIN_US 500U
#define SERVO_MAX_US 2500U

/* Chassis calibration can be narrowed later to prevent endpoint buzzing. */
#define SERVO_CENTER_US 1500U

int servo_init(void)
{
	if (!pwm_is_ready_dt(&servo_pwm))
		return -ENODEV;

	return servo_set_angle_deg(0.0f);
}

int servo_set_angle_deg(float angle_deg)
{
	angle_deg = CLAMP(angle_deg, -45.0f, 45.0f);

	float normalized = (angle_deg + 45.0f) / 90.0f;
	uint32_t pulse_us =
		(uint32_t)(SERVO_MIN_US +
		           normalized * (SERVO_MAX_US - SERVO_MIN_US));

	return pwm_set_dt(&servo_pwm,
			  SERVO_PERIOD_NS,
			  pulse_us * 1000U);
}
