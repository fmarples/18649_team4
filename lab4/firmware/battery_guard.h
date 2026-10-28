#ifndef LAB4_BATTERY_GUARD_H
#define LAB4_BATTERY_GUARD_H
#include <stdbool.h>
#include <stdint.h>

/* Design policy for the selected standard 3S LiPo; not per-cell protection. */
#define BATTERY_STOP_MV 10500u
#define BATTERY_ARM_MV 11100u
#define BATTERY_MAX_MV 12900u
#define BATTERY_MAX_AGE_MS 100u

typedef struct {
    uint32_t last_ms;
    uint32_t pack_mv;
    bool seen;
    bool armed;
    bool fault;
} battery_guard;

void battery_guard_init(battery_guard *g);
void battery_guard_sample(battery_guard *g, uint32_t now_ms,
                          uint32_t pack_mv, bool valid);
bool battery_guard_arm(battery_guard *g, uint32_t now_ms);
bool battery_guard_can_drive(battery_guard *g, uint32_t now_ms);
/* Nominal 100k/10k conversion. vdda_mv must be calibrated, not assumed 3300. */
bool battery_adc_to_mv(uint16_t raw, uint16_t vdda_mv, uint32_t *pack_mv);
#endif
