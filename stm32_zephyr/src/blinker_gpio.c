#include "blinker_gpio.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <errno.h>

#define USER DT_PATH(zephyr_user)
static const struct gpio_dt_spec lamps[] = {
	GPIO_DT_SPEC_GET(USER, front_left_gpios),
	GPIO_DT_SPEC_GET(USER, rear_left_gpios),
	GPIO_DT_SPEC_GET(USER, front_right_gpios),
	GPIO_DT_SPEC_GET(USER, rear_right_gpios),
};
static struct blink_output previous;
static bool have_previous;

int blinker_gpio_init(void)
{
	for (size_t i = 0; i < ARRAY_SIZE(lamps); ++i) {
		if (!gpio_is_ready_dt(&lamps[i])) { return -ENODEV; }
		int rc = gpio_pin_configure_dt(&lamps[i], GPIO_OUTPUT_INACTIVE);
		if (rc != 0) { return rc; }
	}
	have_previous = false;
	return 0;
}

int blinker_gpio_write(struct blink_output output)
{
	if (have_previous && previous.left == output.left && previous.right == output.right) {
		return 0;
	}
	/* Four on-chip writes, with no thread preemption between front/rear.
	 * Interrupts remain enabled; actual skew still requires measurement. */
	int rc = 0;
	k_sched_lock();
	for (size_t i = 0; i < ARRAY_SIZE(lamps); ++i) {
		int result = gpio_pin_set_dt(&lamps[i], i < 2 ? output.left : output.right);
		if (result != 0 && rc == 0) { rc = result; }
	}
	k_sched_unlock();
	if (rc == 0) { previous = output; have_previous = true; }
	return rc;
}
