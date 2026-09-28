/* Exercise the production backend through current_backend_read; only ADC hardware is fake. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/drivers/adc.h>
#include "current_sense.h"

const struct device test_adc = {0};
static int16_t input[3] = {3103, 3332, 2873}; /* ~2.5 V, +1 A, -1 A. */
static bool clip_first_scan, noisy, delayed_isr;
static bool ready;
static int setup_error, read_error;
static uint32_t read_error_channels = 0x103;
static unsigned setup_seen, read_seen;

bool device_is_ready(const struct device *dev)
{
    assert(dev == &test_adc);
    return ready;
}
int adc_channel_setup(const struct device *dev, const struct adc_channel_cfg *cfg)
{
    assert(dev == &test_adc);
    assert(cfg->channel_id == 0 || cfg->channel_id == 1 || cfg->channel_id == 8);
    assert(cfg->gain == ADC_GAIN_1 && cfg->reference == ADC_REF_INTERNAL);
    assert(!cfg->differential);
    setup_seen |= 1U << cfg->channel_id;
    return setup_error;
}
int adc_read(const struct device *dev, const struct adc_sequence *sequence)
{
    assert(dev == &test_adc);
    read_seen |= sequence->channels;
    if (read_error && (sequence->channels & read_error_channels)) return read_error;
    assert(sequence->channels && !(sequence->channels & ~0x103U));
    assert(sequence->resolution == 12);
    assert(sequence->oversampling == 0); /* F401 has no hardware oversampling. */
    const unsigned channel_bits[] = {1U, 2U, 256U};
    unsigned count = 0;
    for (unsigned channel = 0; channel < 3; channel++)
        count += !!(sequence->channels & channel_bits[channel]);
    /* Hardware reproduction: a delayed ISR loses conversions in a non-DMA
     * multi-channel scan and never completes. Return a bounded failure here
     * rather than hanging the host test. Single-channel repeats wait for ISR. */
    if (delayed_isr && count > 1) return -ETIMEDOUT;
    size_t scans = sequence->options ? sequence->options->extra_samplings + 1U : 1U;
    assert(scans == 8);
    assert(sequence->buffer_size == scans * count * sizeof(int16_t));
    int16_t *out = sequence->buffer;
    for (size_t scan = 0; scan < scans; scan++) {
        for (unsigned channel = 0; channel < 3; channel++) {
            if (!(sequence->channels & channel_bits[channel])) continue;
            int16_t value = input[channel];
            if (channel == 0 && noisy) value += scan % 2 ? 200 : -200;
            if (channel == 0 && clip_first_scan && scan == 0) value = 4095;
            *out++ = value;
        }
    }
    return 0;
}
int main(void)
{
    int32_t ma[3] = {1, 2, 3}; uint32_t mask = 7;
#if CONFIG_LAB_CURRENT_CHANNEL_MASK != 7
    ready = true;
    assert(current_backend_read(ma, &mask) == 0);
    assert(mask == CONFIG_LAB_CURRENT_CHANNEL_MASK);
    const unsigned expected_adc = CONFIG_LAB_CURRENT_CHANNEL_MASK == 5 ? 0x101 : 0;
    assert(setup_seen == expected_adc && read_seen == expected_adc);
    assert(ma[1] == CURRENT_UNAVAILABLE);
    if (CONFIG_LAB_CURRENT_CHANNEL_MASK == 5) {
        assert(ma[0] >= -4 && ma[0] <= 4);
        assert(ma[2] >= -1004 && ma[2] <= -996);
    } else {
        assert(ma[0] == CURRENT_UNAVAILABLE && ma[2] == CURRENT_UNAVAILABLE);
    }
    puts("PASS: disconnected channels are neither configured, acquired nor reported");
    return 0;
#endif
    assert(current_backend_read(ma, &mask) == -ENODEV);
    assert(mask == 0);
    for (unsigned i = 0; i < 3; i++) assert(ma[i] == CURRENT_UNAVAILABLE);
    ready = true;
    setup_error = -EIO;
    assert(current_backend_read(ma, &mask) == -EIO);
    assert(mask == 0);
    setup_error = 0;
    delayed_isr = true;
    assert(current_backend_read(ma, &mask) == 0);
    puts("PASS: acquired currents remain available with delayed non-DMA ISR service");
    assert(mask == 7);
    /* Independent ADC-code fixtures, tolerance below one ADC LSB (~4.36 mA). */
    assert(ma[0] >= -4 && ma[0] <= 4);
    assert(ma[1] >= 996 && ma[1] <= 1004);
    assert(ma[2] >= -1004 && ma[2] <= -996);
    puts("PASS: three acquired channels report signed mA in status order");
    noisy = true;
    assert(current_backend_read(ma, &mask) == 0);
    assert(mask == 7 && ma[0] >= -4 && ma[0] <= 4);
    noisy = false;
    puts("PASS: batch averaging rejects alternating ADC noise without historical lag");
    /* Preserve an observed rail clip instead of averaging it into a false
     * lower current. Other channels must continue reporting normally. */
    clip_first_scan = true;
    assert(current_backend_read(ma, &mask) == 0);
    assert(mask == 7 && ma[0] == 4320);
    assert(ma[1] >= 996 && ma[1] <= 1004);
    puts("PASS: ADC saturation reports +4320 mA, with no actuator effect");
    struct current_sample cache;
    current_cache_publish(&cache, ma, mask, 20);
    assert(current_cache_snapshot(&cache, 119, 100).valid_mask == 7);
    assert(current_cache_snapshot(&cache, 120, 100).valid_mask == 0);
    read_error = -EIO;
    assert(current_backend_read(ma, &mask) == -EIO);
    assert(mask == 0);
    for (unsigned i = 0; i < 3; i++) assert(ma[i] == CURRENT_UNAVAILABLE);
    current_cache_publish(&cache, ma, mask, 40);
    assert(current_cache_snapshot(&cache, 40, 100).valid_mask == 0);
    read_error = 0;
    assert(current_backend_read(ma, &mask) == 0 && mask == 7);
    /* A failure after earlier channels succeeded must not publish a partial
     * batch or leave values from the preceding successful call. */
    const uint32_t later_channels[] = {2U, 256U};
    for (unsigned channel = 0; channel < 2; channel++) {
        read_error_channels = later_channels[channel];
        read_error = -EIO;
        assert(current_backend_read(ma, &mask) == -EIO);
        assert(mask == 0);
        for (unsigned i = 0; i < 3; i++) assert(ma[i] == CURRENT_UNAVAILABLE);
        read_error = 0;
        assert(current_backend_read(ma, &mask) == 0 && mask == 7);
        assert(ma[2] >= -1004 && ma[2] <= -996);
    }
    puts("PASS: initialization/read errors invalidate whole batch; retry and expiry work");
    return 0;
}
