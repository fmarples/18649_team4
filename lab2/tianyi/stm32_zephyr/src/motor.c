#include "motor.h"
#include "encoder.h"

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/sys/util.h>
#include <math.h>

/*
 * User pinout:
 * left PWM=PB4/TIM3_CH1, left IN1=PC7, IN2=PA6
 * right PWM=PB10/TIM2_CH3, right IN3=PC1, IN4=PC0
 */
static const struct pwm_dt_spec left_pwm =
	PWM_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), left_motor_pwm);
static const struct pwm_dt_spec right_pwm =
	PWM_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), right_motor_pwm);

static const struct gpio_dt_spec left_in1 =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), left_motor_in1_gpios);
static const struct gpio_dt_spec left_in2 =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), left_motor_in2_gpios);
static const struct gpio_dt_spec right_in3 =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), right_motor_in3_gpios);
static const struct gpio_dt_spec right_in4 =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), right_motor_in4_gpios);

#define PWM_PERIOD_US 1000U

#define KP 900.0f
#define KI 300.0f
#define INTEGRAL_LIMIT 0.35f

static float left_target;
static float right_target;
static float left_integral;
static float right_integral;
static bool braking;

static struct k_work_delayable control_work;

static int pwm_set_percent(const struct pwm_dt_spec *pwm, float percent)
{
	percent = CLAMP(percent, 0.0f, 100.0f);

	uint32_t period = PWM_PERIOD_US * 1000U;
	uint32_t pulse = (uint32_t)((percent / 100.0f) * period);

	return pwm_set_dt(pwm, period, pulse);
}

static int set_motor(const struct pwm_dt_spec *pwm,
		     const struct gpio_dt_spec *in1,
		     const struct gpio_dt_spec *in2,
		     float target,
		     float measured,
		     float *integral)
{
	const float dt = 0.001f;
	float error = target - measured;

	*integral += error * dt;
	*integral = CLAMP(*integral, -INTEGRAL_LIMIT, INTEGRAL_LIMIT);

	float command = KP * error + KI * (*integral);

	bool reverse = command < 0.0f;
	float magnitude = fabsf(command);

	magnitude = CLAMP(magnitude, 0.0f, 100.0f);

	(void)gpio_pin_set_dt(in1, reverse ? 0 : 1);
	(void)gpio_pin_set_dt(in2, reverse ? 1 : 0);

	return pwm_set_percent(pwm, magnitude);
}

static void control_work_fn(struct k_work *work)
{
	ARG_UNUSED(work);

	if (braking) {
		k_work_reschedule(&control_work, K_MSEC(1));
		return;
	}

	float lv = encoder_left_velocity_mps();
	float rv = encoder_right_velocity_mps();

	(void)set_motor(&left_pwm, &left_in1, &left_in2,
	                left_target, lv, &left_integral);
	(void)set_motor(&right_pwm, &right_in3, &right_in4,
	                right_target, rv, &right_integral);

	k_work_reschedule(&control_work, K_MSEC(1));
}

int motor_init(void)
{
	if (!pwm_is_ready_dt(&left_pwm) ||
	    !pwm_is_ready_dt(&right_pwm) ||
	    !gpio_is_ready_dt(&left_in1) ||
	    !gpio_is_ready_dt(&left_in2) ||
	    !gpio_is_ready_dt(&right_in3) ||
	    !gpio_is_ready_dt(&right_in4))
		return -ENODEV;

	if (gpio_pin_configure_dt(&left_in1, GPIO_OUTPUT_LOW) ||
	    gpio_pin_configure_dt(&left_in2, GPIO_OUTPUT_LOW) ||
	    gpio_pin_configure_dt(&right_in3, GPIO_OUTPUT_LOW) ||
	    gpio_pin_configure_dt(&right_in4, GPIO_OUTPUT_LOW))
		return -EIO;

	left_target = right_target = 0.0f;
	left_integral = right_integral = 0.0f;
	braking = true;

	(void)pwm_set_percent(&left_pwm, 0.0f);
	(void)pwm_set_percent(&right_pwm, 0.0f);

	k_work_init_delayable(&control_work, control_work_fn);
	k_work_schedule(&control_work, K_MSEC(1));

	return 0;
}

int motor_set_velocity(float left_mps, float right_mps)
{
	left_target = left_mps;
	right_target = right_mps;
	left_integral = 0.0f;
	right_integral = 0.0f;
	braking = false;
	return 0;
}

int motor_dynamic_brake(void)
{
	braking = true;
	left_target = right_target = 0.0f;
	left_integral = right_integral = 0.0f;

	/*
	 * L298N dynamic-brake state used here: both bridge inputs HIGH with
	 * PWM disabled. Verify this state on the actual module/wiring before
	 * treating it as the final safety configuration.
	 */
	(void)pwm_set_percent(&left_pwm, 0.0f);
	(void)pwm_set_percent(&right_pwm, 0.0f);

	(void)gpio_pin_set_dt(&left_in1, 1);
	(void)gpio_pin_set_dt(&left_in2, 1);
	(void)gpio_pin_set_dt(&right_in3, 1);
	(void)gpio_pin_set_dt(&right_in4, 1);

	return 0;
}
