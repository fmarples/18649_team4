#include "current_sense.h"
#include <zephyr/drivers/adc.h>
#include <errno.h>

static const struct device *const adc = DEVICE_DT_GET(DT_NODELABEL(adc1));
/* Status order: PA0, PA1, PB0. */
static const uint8_t channels[CURRENT_CHANNELS] = {0, 1, 8};
static const int32_t zero_mv[CURRENT_CHANNELS] = {
    CONFIG_LAB_CURRENT_LEFT_ZERO_MV, CONFIG_LAB_CURRENT_RIGHT_ZERO_MV,
    CONFIG_LAB_CURRENT_SERVO_ZERO_MV,
};
static const int32_t sensitivity[CURRENT_CHANNELS] = {
    CONFIG_LAB_CURRENT_LEFT_SENSITIVITY, CONFIG_LAB_CURRENT_RIGHT_SENSITIVITY,
    CONFIG_LAB_CURRENT_SERVO_SENSITIVITY,
};

/* Called only by the current workqueue. Acquire actual ADC samples, then apply
 * configured nominal/bench calibration. No actuator policy or shared lock here. */
int current_backend_read(int32_t ma[3], uint32_t *valid_mask)
{
    static bool configured;
    for (unsigned i = 0; i < CURRENT_CHANNELS; i++) ma[i] = CURRENT_UNAVAILABLE;
    *valid_mask = 0;
    if (!CONFIG_LAB_CURRENT_CHANNEL_MASK) return 0;
    if (!device_is_ready(adc)) return -ENODEV;
    if (!configured) {
        for (unsigned i = 0; i < CURRENT_CHANNELS; i++) {
            if (!(CONFIG_LAB_CURRENT_CHANNEL_MASK & (1U << i))) continue;
            const struct adc_channel_cfg config = {
                .gain = ADC_GAIN_1,
                .reference = ADC_REF_INTERNAL, /* STM32 driver uses VDDA. */
                .acquisition_time = ADC_ACQ_TIME(ADC_ACQ_TIME_TICKS, 480),
                .channel_id = channels[i],
            };
            int error = adc_channel_setup(adc, &config);
            if (error) return error;
        }
        configured = true;
    }
    /* One channel per sequence: the non-DMA STM32 driver must consume each
     * conversion before starting the next. Multi-channel scans can overrun
     * during ISR latency and leave adc_read waiting forever for a lost sample.
     * Keep eight samples per channel and no cross-period filter state. */
    enum { SCANS = 8 };
    int16_t raw[CURRENT_CHANNELS][SCANS];
    const struct adc_sequence_options options = {.extra_samplings = SCANS - 1};
    for (unsigned i = 0; i < CURRENT_CHANNELS; i++) {
        if (!(CONFIG_LAB_CURRENT_CHANNEL_MASK & (1U << i))) continue;
        const struct adc_sequence sequence = {
            .options = &options,
            .channels = 1U << channels[i],
            .buffer = raw[i],
            .buffer_size = sizeof(raw[i]),
            .resolution = 12,
        };
        int error = adc_read(adc, &sequence);
        if (error) return error;
    }
    for (unsigned i = 0; i < CURRENT_CHANNELS; i++) {
        if (!(CONFIG_LAB_CURRENT_CHANNEL_MASK & (1U << i))) continue;
        int32_t sum = 0;
        bool clipped = false;
        for (unsigned scan = 0; scan < SCANS; scan++) {
            sum += raw[i][scan];
            clipped |= raw[i][scan] == 4095;
        }
        int64_t uv = (int64_t)sum * DT_PROP(DT_NODELABEL(adc1), vref_mv) * 1000 /
                     (4096 * SCANS);
        int64_t delta_uv = uv - zero_mv[i] * 1000;
        int32_t value = (delta_uv + (delta_uv >= 0 ? sensitivity[i] / 2 : -sensitivity[i] / 2)) /
                        sensitivity[i];
        /* User-selected reporting ceiling. A rail clip is a lower-bound
         * indication, not an exact measurement and never a motor cutoff. */
        ma[i] = clipped || value > CURRENT_REPORT_MAX_MA ? CURRENT_REPORT_MAX_MA : value;
        *valid_mask |= 1U << i;
    }
    return 0;
}
