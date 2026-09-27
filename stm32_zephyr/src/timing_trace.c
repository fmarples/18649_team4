#include "timing_trace.h"
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/atomic.h>

static atomic_t errors;
#if defined(CONFIG_LAB_TIMING_GPIO)
static const struct gpio_dt_spec pins[] = {
    GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), cmd_rx_gpios),
    GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), pwm_set_gpios),
};
static bool ready;
/* Each level has exactly one writer; set/clear uses atomic STM32 BSRR writes.
 * Do not use port ODR read/modify/write toggles: PC0/PC1/PC7 drive the motors. */
static bool levels[2];
int timing_trace_init(void)
{
    for (unsigned i = 0; i < 2; i++) {
        int rc = gpio_is_ready_dt(&pins[i]) ?
            gpio_pin_configure_dt(&pins[i], GPIO_OUTPUT_INACTIVE) : -ENODEV;
        if (rc) { atomic_inc(&errors); return rc; }
    }
    ready = true;
    return 0;
}
static void mark(unsigned i)
{
    if (!ready) { return; }
    bool next = !levels[i];
    if (gpio_pin_set_dt(&pins[i], next)) { atomic_inc(&errors); }
    else { levels[i] = next; }
}
void timing_trace_command(void) { mark(0); }
void timing_trace_pwm(void) { mark(1); }
#else
int timing_trace_init(void) { return 0; }
void timing_trace_command(void) {}
void timing_trace_pwm(void) {}
#endif
uint32_t timing_trace_errors(void) { return (uint32_t)atomic_get(&errors); }
