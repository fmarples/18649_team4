#include "encoder.h"
#include <zephyr/kernel.h>

/* TODO: Implement these using your encoder GPIO/interrupts or timer inputs.
 * The lab requires velocity control based on the average of the two encoders. */
static volatile int32_t left_count;
static volatile int32_t right_count;
static int32_t last_left;
static int32_t last_right;
static int64_t last_time_ms;

void encoder_init(void) {
    /* TODO: configure encoder A/B inputs and ISRs for your hardware. */
    left_count = 0;
    right_count = 0;
    last_left = 0;
    last_right = 0;
    last_time_ms = k_uptime_get();
}

int32_t encoder_get_left_count(void) { return left_count; }
int32_t encoder_get_right_count(void) { return right_count; }

float encoder_get_average_velocity_mps(void) {
    int64_t now = k_uptime_get();
    int64_t dt_ms = now - last_time_ms;
    if (dt_ms <= 0) return 0.0f;

    int32_t dl = left_count - last_left;
    int32_t dr = right_count - last_right;
    last_left = left_count;
    last_right = right_count;
    last_time_ms = now;

    /* TODO: Replace with your measured counts/rev and wheel circumference. */
    const float COUNTS_PER_REV = 1000.0f;
    const float WHEEL_CIRCUMFERENCE_M = 0.20f;
    float rev_l = (float)dl / COUNTS_PER_REV;
    float rev_r = (float)dr / COUNTS_PER_REV;
    float dist_m = ((rev_l + rev_r) * 0.5f) * WHEEL_CIRCUMFERENCE_M;
    return dist_m / ((float)dt_ms / 1000.0f);
}
