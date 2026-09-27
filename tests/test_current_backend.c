/* Exercise the production backend through current_backend_read; only ADC hardware is fake. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/drivers/adc.h>
#include "current_sense.h"

const struct device test_adc = {0};
static int16_t input[3] = {3103, 3332, 2873}; /* ~2.5 V, +1 A, -1 A. */
static bool clip_first_scan, noisy;
static bool ready;
static int setup_error, read_error;

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
    return setup_error;
}
int adc_read(const struct device *dev, const struct adc_sequence *sequence)
{
    assert(dev == &test_adc);
    if (read_error) return read_error;
    assert(sequence->channels == 0x103 && sequence->resolution == 12);
    assert(sequence->oversampling == 0); /* F401 has no hardware oversampling. */
    size_t scans = sequence->options ? sequence->options->extra_samplings + 1U : 1U;
    assert(sequence->buffer_size == scans * sizeof(input));
    for (size_t i = 0; i < scans; i++) {
        memcpy((int16_t *)sequence->buffer + i * 3, input, sizeof(input));
        if (noisy) ((int16_t *)sequence->buffer)[i * 3] += i % 2 ? 200 : -200;
    }
    if (clip_first_scan) ((int16_t *)sequence->buffer)[0] = 4095;
    return 0;
}
int main(void)
{
    int32_t ma[3] = {1, 2, 3}; uint32_t mask = 7;
    assert(current_backend_read(ma, &mask) == -ENODEV);
    assert(mask == 0);
    for (unsigned i = 0; i < 3; i++) assert(ma[i] == CURRENT_UNAVAILABLE);
    ready = true;
    setup_error = -EIO;
    assert(current_backend_read(ma, &mask) == -EIO);
    assert(mask == 0);
    setup_error = 0;
    assert(current_backend_read(ma, &mask) == 0);
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
    puts("PASS: initialization/read errors invalidate data; retry and expiry work");
    return 0;
}
