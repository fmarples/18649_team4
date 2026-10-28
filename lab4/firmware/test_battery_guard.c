#include "battery_guard.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    battery_guard g;
    uint32_t mv;
    battery_guard_init(&g);
    assert(!battery_guard_can_drive(&g, 0));
    assert(!battery_guard_arm(&g, 0));
    battery_guard_sample(&g, 0, 11099, true);
    assert(!battery_guard_arm(&g, 0));
    battery_guard_sample(&g, 10, 11100, true);
    assert(battery_guard_arm(&g, 10));
    assert(battery_guard_can_drive(&g, 110));
    assert(!battery_guard_can_drive(&g, 111));
    battery_guard_sample(&g, 112, 12600, true);
    assert(!battery_guard_arm(&g, 112)); /* recovery cannot clear the latch */

    battery_guard_init(&g);
    battery_guard_sample(&g, 0, 12600, true);
    assert(battery_guard_arm(&g, 0));
    battery_guard_sample(&g, 10, 10501, true);
    assert(battery_guard_can_drive(&g, 10));
    battery_guard_sample(&g, 20, 10500, true);
    assert(!battery_guard_can_drive(&g, 20));
    battery_guard_sample(&g, 30, 11500, true);
    assert(!battery_guard_arm(&g, 30));

    battery_guard_init(&g);
    battery_guard_sample(&g, UINT32_MAX - 20u, 12600, true);
    assert(battery_guard_arm(&g, UINT32_MAX - 20u));
    battery_guard_sample(&g, 5, 12000, true);
    assert(battery_guard_can_drive(&g, 5));
    battery_guard_sample(&g, 106, 12000, true); /* missed sampling deadline */
    assert(!battery_guard_can_drive(&g, 106));

    battery_guard_init(&g);
    battery_guard_sample(&g, 0, 12600, false);
    assert(!battery_guard_arm(&g, 0));
    battery_guard_init(&g);
    battery_guard_sample(&g, 0, 12901, true);
    assert(!battery_guard_arm(&g, 0));
    assert(!battery_adc_to_mv(4095, 3300, &mv));
    assert(!battery_adc_to_mv(1000, 0, &mv));
    assert(!battery_adc_to_mv(1000, 3300, 0));
    assert(battery_adc_to_mv(0, 3300, &mv) && mv == 0);
    assert(battery_adc_to_mv(1421, 3300, &mv));
    assert(mv >= 12590 && mv <= 12610);
    puts("PASS: battery guard startup, thresholds, invalid/stale samples, latch, clock wrap and ADC conversion");
    return 0;
}
