/* GPIO LEDs and test points; every pin starts inactive (low). */
#include "timing_trace.h"
#include <zephyr/drivers/gpio.h>
#include <zephyr/devicetree.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/util.h>
#include <errno.h>

#define USER DT_PATH(zephyr_user)
static const struct gpio_dt_spec pins[] = {
    [TP_CAN_RX_A] = GPIO_DT_SPEC_GET(USER, can_rx_a_gpios),
    [TP_CAN_RX_B] = GPIO_DT_SPEC_GET(USER, can_rx_b_gpios),
    [TP_CAN_TX_A] = GPIO_DT_SPEC_GET(USER, can_tx_a_gpios),
    [TP_CAN_TX_B] = GPIO_DT_SPEC_GET(USER, can_tx_b_gpios),
    [TP_DEG_A] = GPIO_DT_SPEC_GET(USER, degraded_a_gpios),
    [TP_DEG_B] = GPIO_DT_SPEC_GET(USER, degraded_b_gpios),
    [TP_ERR] = GPIO_DT_SPEC_GET(USER, error_gpios),
    [TP_STEER] = GPIO_DT_SPEC_GET(USER, steer_task_gpios),
    [TP_PWM_SET] = GPIO_DT_SPEC_GET(USER, pwm_set_gpios),
    [TP_DIR_A] = GPIO_DT_SPEC_GET(USER, dir_a_gpios),
    [TP_PID] = GPIO_DT_SPEC_GET(USER, pid_gpios),
    [TP_FL] = GPIO_DT_SPEC_GET(USER, front_left_gpios),
    [TP_FR] = GPIO_DT_SPEC_GET(USER, front_right_gpios),
    [TP_RL] = GPIO_DT_SPEC_GET(USER, rear_left_gpios),
    [TP_RR] = GPIO_DT_SPEC_GET(USER, rear_right_gpios),
    [TP_RELAY_TX] = GPIO_DT_SPEC_GET(USER, relay_tx_gpios),
    [TP_TASK_PROBE] = GPIO_DT_SPEC_GET(USER, task_probe_gpios),
};
/* Toggles come from several threads; one atomic bit per pin keeps levels consistent. */
static atomic_t levels;

int lab3_trace_init(void)
{
    for (unsigned i = 0; i < ARRAY_SIZE(pins); ++i) {
        if (!gpio_is_ready_dt(&pins[i])) return -ENODEV;
        int rc = gpio_pin_configure_dt(&pins[i], GPIO_OUTPUT_INACTIVE);
        if (rc) return rc;
    }
    return 0;
}

void lab3_trace_toggle(unsigned i)
{
    if (i >= ARRAY_SIZE(pins)) return;
    bool was = (atomic_xor(&levels, BIT(i)) & BIT(i)) != 0;
    (void)gpio_pin_set_dt(&pins[i], !was);
}

void lab3_trace_set(unsigned i, int active)
{
    if (i >= ARRAY_SIZE(pins)) return;
    atomic_set_bit_to(&levels, i, active);
    (void)gpio_pin_set_dt(&pins[i], !!active);
}
