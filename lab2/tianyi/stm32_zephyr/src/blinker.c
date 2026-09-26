#include "blinker.h"

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>

static const struct gpio_dt_spec fl =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), front_left_blinker_gpios);
static const struct gpio_dt_spec fr =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), front_right_blinker_gpios);
static const struct gpio_dt_spec rl =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), rear_left_blinker_gpios);
static const struct gpio_dt_spec rr =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), rear_right_blinker_gpios);

static struct k_work_delayable flash_work;

static bool left_requested;
static bool right_requested;
static bool hazard_requested;
static bool flash_state;

static bool left_button_prev;
static bool right_button_prev;

static bool left_armed;
static bool right_armed;

static float turn_threshold = 30.0f;

static void outputs(bool left, bool right, bool hazard)
{
	if (hazard) {
		(void)gpio_pin_set_dt(&fl, flash_state);
		(void)gpio_pin_set_dt(&fr, flash_state);
		(void)gpio_pin_set_dt(&rl, flash_state);
		(void)gpio_pin_set_dt(&rr, flash_state);
		return;
	}

	(void)gpio_pin_set_dt(&fl, left && flash_state);
	(void)gpio_pin_set_dt(&rl, left && flash_state);
	(void)gpio_pin_set_dt(&fr, right && flash_state);
	(void)gpio_pin_set_dt(&rr, right && flash_state);
}

static void flash_work_fn(struct k_work *work)
{
	ARG_UNUSED(work);

	flash_state = !flash_state;
	outputs(left_requested, right_requested, hazard_requested);

	/*
	 * Normal turn signal: 1 Hz, 50% duty cycle.
	 * Hazard/error: 2 Hz, 50% duty cycle.
	 */
	k_work_reschedule(&flash_work,
	                  K_MSEC(hazard_requested ? 250 : 500));
}

int blinker_init(void)
{
	if (!gpio_is_ready_dt(&fl) ||
	    !gpio_is_ready_dt(&fr) ||
	    !gpio_is_ready_dt(&rl) ||
	    !gpio_is_ready_dt(&rr))
		return -ENODEV;

	if (gpio_pin_configure_dt(&fl, GPIO_OUTPUT_INACTIVE) ||
	    gpio_pin_configure_dt(&fr, GPIO_OUTPUT_INACTIVE) ||
	    gpio_pin_configure_dt(&rl, GPIO_OUTPUT_INACTIVE) ||
	    gpio_pin_configure_dt(&rr, GPIO_OUTPUT_INACTIVE))
		return -EIO;

	left_requested = right_requested = hazard_requested = false;
	flash_state = false;
	left_button_prev = right_button_prev = false;
	left_armed = right_armed = false;

	k_work_init_delayable(&flash_work, flash_work_fn);
	k_work_schedule(&flash_work, K_MSEC(250));

	return 0;
}

int blinker_set_left(bool on)
{
	left_requested = on;
	if (on)
		right_requested = false;
	return 0;
}

int blinker_set_right(bool on)
{
	right_requested = on;
	if (on)
		left_requested = false;
	return 0;
}

int blinker_set_hazard(bool on)
{
	hazard_requested = on;
	if (on) {
		left_requested = false;
		right_requested = false;
	}
	return 0;
}

int blinker_update(bool left_button, bool right_button, float steering_deg)
{
	/*
	 * Button actions are edge-triggered so repeatedly receiving the same
	 * wheel packet does not continuously re-arm a self-cancelled signal.
	 */
	if (left_button && !left_button_prev) {
		left_armed = true;
		right_armed = false;
		left_requested = true;
		right_requested = false;
	}

	if (right_button && !right_button_prev) {
		right_armed = true;
		left_armed = false;
		right_requested = true;
		left_requested = false;
	}

	left_button_prev = left_button;
	right_button_prev = right_button;

	/*
	 * Self-cancel after the wheel passes the turn threshold and then returns
	 * through the threshold toward center.
	 */
	if (left_armed && steering_deg <= -turn_threshold)
		left_armed = false;

	if (right_armed && steering_deg >= turn_threshold)
		right_armed = false;

	if (!left_button && !right_button) {
		if (!left_armed && left_requested &&
		    steering_deg > -turn_threshold)
			left_requested = false;

		if (!right_armed && right_requested &&
		    steering_deg < turn_threshold)
			right_requested = false;
	}

	return 0;
}
