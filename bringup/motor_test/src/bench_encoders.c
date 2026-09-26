/* Decoder reused from the independently hand-turn-verified encoder_test. */
#include <errno.h>
#include <stdint.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include "bench_encoders.h"

struct encoder {
    struct gpio_dt_spec a;
    struct gpio_dt_spec b;
    struct gpio_callback callback_a;
    struct gpio_callback callback_b;
    uint8_t previous;
    int32_t count;
    uint32_t invalid;
    uint32_t errors;
};

static struct encoder encoders[] = {
    {.a = GPIO_DT_SPEC_GET(DT_NODELABEL(left_a), gpios),
     .b = GPIO_DT_SPEC_GET(DT_NODELABEL(left_b), gpios)},
    {.a = GPIO_DT_SPEC_GET(DT_NODELABEL(right_a), gpios),
     .b = GPIO_DT_SPEC_GET(DT_NODELABEL(right_b), gpios)},
};
static struct k_spinlock counter_lock;

/* Four counts per complete A/B cycle. Positive: 00 -> 01 -> 11 -> 10 -> 00.
 * Physical vehicle-forward polarity is deliberately not assumed here. */
static const int8_t step[16] = {
     0,  1, -1,  0,
    -1,  0,  0,  1,
     1,  0,  0, -1,
     0, -1,  1,  0,
};

static int read_ab(const struct encoder *encoder)
{
    int a = gpio_pin_get_dt(&encoder->a);
    int b = gpio_pin_get_dt(&encoder->b);

    if (a < 0) {
        return a;
    }
    if (b < 0) {
        return b;
    }
    return (a << 1) | b;
}

static void on_edge(const struct device *port, struct gpio_callback *callback,
                    gpio_port_pins_t pins)
{
    ARG_UNUSED(port);
    ARG_UNUSED(pins);

    for (size_t i = 0; i < ARRAY_SIZE(encoders); ++i) {
        struct encoder *encoder = &encoders[i];
        if (callback != &encoder->callback_a && callback != &encoder->callback_b) {
            continue;
        }

        k_spinlock_key_t key = k_spin_lock(&counter_lock);
        int current = read_ab(encoder);
        if (current < 0) {
            encoder->errors++;
        } else {
            /* Both bits changing means an edge was missed or signals are noisy.
             * Record the fault and resync without inventing movement. */
            if ((encoder->previous ^ current) == 3) {
                encoder->invalid++;
            } else {
                encoder->count += step[(encoder->previous << 2) | current];
            }
            encoder->previous = (uint8_t)current;
        }
        k_spin_unlock(&counter_lock, key);
        return;
    }
}

static int init_encoder(struct encoder *encoder)
{
    if (!gpio_is_ready_dt(&encoder->a) || !gpio_is_ready_dt(&encoder->b)) {
        return -ENODEV;
    }
    int ret = gpio_pin_configure_dt(&encoder->a, GPIO_INPUT);
    if (ret < 0) {
        return ret;
    }
    ret = gpio_pin_configure_dt(&encoder->b, GPIO_INPUT);
    if (ret < 0) {
        return ret;
    }

    int initial = read_ab(encoder);
    if (initial < 0) {
        return initial;
    }
    encoder->previous = (uint8_t)initial;
    gpio_init_callback(&encoder->callback_a, on_edge, BIT(encoder->a.pin));
    gpio_init_callback(&encoder->callback_b, on_edge, BIT(encoder->b.pin));
    ret = gpio_add_callback(encoder->a.port, &encoder->callback_a);
    if (ret < 0) {
        return ret;
    }
    ret = gpio_add_callback(encoder->b.port, &encoder->callback_b);
    if (ret < 0) {
        return ret;
    }
    ret = gpio_pin_interrupt_configure_dt(&encoder->a, GPIO_INT_EDGE_BOTH);
    if (ret < 0) {
        return ret;
    }
    return gpio_pin_interrupt_configure_dt(&encoder->b, GPIO_INT_EDGE_BOTH);
}

int bench_encoders_init(void)
{
    for (size_t i = 0; i < ARRAY_SIZE(encoders); ++i) {
        int ret = init_encoder(&encoders[i]);
        if (ret < 0) { return ret; }
    }
    return 0;
}

int bench_encoders_read(struct bench_encoder_sample *sample)
{
    sample->errors = 0;
    k_spinlock_key_t key = k_spin_lock(&counter_lock);
    sample->time_ms = k_uptime_get();
    for (size_t i = 0; i < ARRAY_SIZE(encoders); ++i) {
        sample->ab[i] = read_ab(&encoders[i]);
        if (sample->ab[i] < 0) { encoders[i].errors++; }
        sample->counts[i] = encoders[i].count;
        sample->invalid[i] = encoders[i].invalid;
        sample->errors += encoders[i].errors;
    }
    k_spin_unlock(&counter_lock, key);
    return sample->errors ? -EIO : 0;
}
