/* GPIO probe mapping is defined in boards/nucleo_f401re.overlay. */
#include "timing_trace.h"
#include <zephyr/drivers/gpio.h>
#include <zephyr/devicetree.h>
#include <zephyr/sys/util.h>
#include <errno.h>
static const struct gpio_dt_spec pins[] = {
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), can_rx_a_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), can_rx_b_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), can_tx_a_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), can_tx_b_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), degraded_a_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), degraded_b_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), error_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), srv_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), pwm_set_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), dir_a_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), pid_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), front_left_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), front_right_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), rear_left_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), rear_right_gpios),
 GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), relay_tx_gpios),
};
static int levels[ARRAY_SIZE(pins)];
int lab3_trace_init(void) {
 for (unsigned i=0; i<ARRAY_SIZE(pins); ++i) {
  if (!gpio_is_ready_dt(&pins[i])) return -ENODEV;
  int rc = gpio_pin_configure_dt(&pins[i], GPIO_OUTPUT_INACTIVE); if (rc) return rc;
  levels[i]=0;
 }
 return 0;
}
void lab3_trace_toggle(unsigned i) {
 if (i >= ARRAY_SIZE(pins)) return;
 levels[i] = !levels[i]; (void)gpio_pin_set_dt(&pins[i], levels[i]);
}
void lab3_trace_set(unsigned i, int active) {
 if (i >= ARRAY_SIZE(pins)) return;
 levels[i] = !!active; (void)gpio_pin_set_dt(&pins[i], levels[i]);
}
