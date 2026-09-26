#include "encoder.h"

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <errno.h>

#define ENCODER_COUNTS_PER_REV 3960.0f
#define WHEEL_CIRCUMFERENCE_M  0.23561945f
#define SAMPLE_MS              10U

static const struct gpio_dt_spec left_a =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), left_encoder_a_gpios);
static const struct gpio_dt_spec left_b =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), left_encoder_b_gpios);
static const struct gpio_dt_spec right_a =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), right_encoder_a_gpios);
static const struct gpio_dt_spec right_b =
	GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), right_encoder_b_gpios);

static struct gpio_callback left_a_cb;
static struct gpio_callback left_b_cb;
static struct gpio_callback right_a_cb;
static struct gpio_callback right_b_cb;

static volatile int32_t left_count;
static volatile int32_t right_count;
static volatile uint8_t left_last;
static volatile uint8_t right_last;

static float left_velocity;
static float right_velocity;
static int32_t left_prev;
static int32_t right_prev;

static struct k_work_delayable sample_work;

#ifndef ENCODER_DIRECTION_SIGN
#define ENCODER_DIRECTION_SIGN 1
#endif

static uint8_t read_pair(const struct gpio_dt_spec *a,
                         const struct gpio_dt_spec *b)
{
	return (uint8_t)((gpio_pin_get_dt(a) ? 1U : 0U) |
	                 ((gpio_pin_get_dt(b) ? 1U : 0U) << 1));
}

static int8_t transition_delta(uint8_t old_state, uint8_t new_state)
{
	static const int8_t table[16] = {
		 0, -1,  1,  0,
		 1,  0,  0, -1,
		-1,  0,  0,  1,
		 0,  1, -1,  0
	};

	return table[((old_state & 3U) << 2) | (new_state & 3U)]
	       * ENCODER_DIRECTION_SIGN;
}

static void left_edge(const struct device *port,
                      struct gpio_callback *cb,
                      gpio_port_pins_t pins)
{
	ARG_UNUSED(port);
	ARG_UNUSED(cb);
	ARG_UNUSED(pins);

	uint8_t now = read_pair(&left_a, &left_b);
	left_count += transition_delta(left_last, now);
	left_last = now;
}

static void right_edge(const struct device *port,
                       struct gpio_callback *cb,
                       gpio_port_pins_t pins)
{
	ARG_UNUSED(port);
	ARG_UNUSED(cb);
	ARG_UNUSED(pins);

	uint8_t now = read_pair(&right_a, &right_b);
	right_count += transition_delta(right_last, now);
	right_last = now;
}

static void sample_work_fn(struct k_work *work)
{
	ARG_UNUSED(work);

	int32_t lc = left_count;
	int32_t rc = right_count;

	int32_t ld = lc - left_prev;
	int32_t rd = rc - right_prev;

	left_prev = lc;
	right_prev = rc;

	const float seconds = SAMPLE_MS / 1000.0f;

	left_velocity =
		((float)ld / ENCODER_COUNTS_PER_REV) *
		WHEEL_CIRCUMFERENCE_M / seconds;

	right_velocity =
		((float)rd / ENCODER_COUNTS_PER_REV) *
		WHEEL_CIRCUMFERENCE_M / seconds;

	k_work_reschedule(&sample_work, K_MSEC(SAMPLE_MS));
}

int encoder_init(void)
{
	if (!gpio_is_ready_dt(&left_a) ||
	    !gpio_is_ready_dt(&left_b) ||
	    !gpio_is_ready_dt(&right_a) ||
	    !gpio_is_ready_dt(&right_b))
		return -ENODEV;

	if (gpio_pin_configure_dt(&left_a, GPIO_INPUT) ||
	    gpio_pin_configure_dt(&left_b, GPIO_INPUT) ||
	    gpio_pin_configure_dt(&right_a, GPIO_INPUT) ||
	    gpio_pin_configure_dt(&right_b, GPIO_INPUT))
		return -EIO;

	left_last = read_pair(&left_a, &left_b);
	right_last = read_pair(&right_a, &right_b);

	gpio_init_callback(&left_a_cb, left_edge, BIT(left_a.pin));
	gpio_init_callback(&left_b_cb, left_edge, BIT(left_b.pin));
	gpio_init_callback(&right_a_cb, right_edge, BIT(right_a.pin));
	gpio_init_callback(&right_b_cb, right_edge, BIT(right_b.pin));

	if (gpio_add_callback(left_a.port, &left_a_cb) ||
	    gpio_add_callback(left_b.port, &left_b_cb) ||
	    gpio_add_callback(right_a.port, &right_a_cb) ||
	    gpio_add_callback(right_b.port, &right_b_cb))
		return -EIO;

	if (gpio_pin_interrupt_configure_dt(&left_a,
					    GPIO_INT_EDGE_BOTH) ||
	    gpio_pin_interrupt_configure_dt(&left_b,
					    GPIO_INT_EDGE_BOTH) ||
	    gpio_pin_interrupt_configure_dt(&right_a,
					    GPIO_INT_EDGE_BOTH) ||
	    gpio_pin_interrupt_configure_dt(&right_b,
					    GPIO_INT_EDGE_BOTH))
		return -EIO;

	left_count = right_count = 0;
	left_prev = right_prev = 0;
	left_velocity = right_velocity = 0.0f;

	k_work_init_delayable(&sample_work, sample_work_fn);
	k_work_schedule(&sample_work, K_MSEC(SAMPLE_MS));

	return 0;
}

int32_t encoder_left_count(void) { return left_count; }
int32_t encoder_right_count(void) { return right_count; }
float encoder_left_velocity_mps(void) { return left_velocity; }
float encoder_right_velocity_mps(void) { return right_velocity; }

float encoder_get_average_velocity_mps(void)
{
	return 0.5f * (left_velocity + right_velocity);
}
