/* Host-only ADC boundary double. Production builds use Zephyr's real header. */
#ifndef TEST_CURRENT_ADC_H
#define TEST_CURRENT_ADC_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct device { int unused; };
extern const struct device test_adc;
#define DT_NODELABEL(name) name
#define DEVICE_DT_GET(node) (&test_adc)
#define DT_PROP(node, prop) 3300
#define ADC_GAIN_1 1
#define ADC_REF_INTERNAL 0
#define ADC_ACQ_TIME_TICKS 1
#define ADC_ACQ_TIME(unit, value) (value)

struct adc_channel_cfg {
    int gain, reference;
    uint16_t acquisition_time;
    uint8_t channel_id;
    bool differential;
};
struct adc_sequence_options { uint32_t interval_us; uint16_t extra_samplings; };
struct adc_sequence {
    const struct adc_sequence_options *options;
    uint32_t channels;
    void *buffer;
    size_t buffer_size;
    uint8_t resolution, oversampling;
    bool calibrate;
};
bool device_is_ready(const struct device *dev);
int adc_channel_setup(const struct device *dev, const struct adc_channel_cfg *cfg);
int adc_read(const struct device *dev, const struct adc_sequence *sequence);
#endif
