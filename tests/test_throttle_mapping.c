/* Public raw-pedal mapping contract; expected values use the measured 23 RPM
 * sustaining speed and user-selected 300 RPM full-pedal endpoint. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "throttle_mapping.h"

int main(void)
{
    /* Raw pedal span is 65535. A 23/300 threshold lies between pressed
     * counts 5024 and 5025: raw 27743 must stop; raw 27742 may drive. */
    assert(pedal_target_mrpm(32767, 32767) == 0);
    assert(pedal_target_mrpm(27743, 32767) == 0);
    assert(pedal_target_mrpm(27742, 32767) == 23002);
    assert(pedal_target_mrpm(0, 32767) == 149997);
    assert(pedal_target_mrpm(-1, 32767) == 150002);
    assert(pedal_target_mrpm(-32768, 32767) == 300000);
    /* Any brake press wins, even with full throttle. */
    assert(pedal_target_mrpm(-32768, 32766) == 0);
    assert(pedal_target_mrpm(-32768, -32768) == 0);

    uint32_t previous = 0;
    for (int32_t raw = 32767; raw >= -32768; --raw) {
        uint32_t target = pedal_target_mrpm(raw, 32767);
        assert(target >= previous);
        assert(target == 0 || (target >= 23000 && target <= 300000));
        if (raw > 27742) { assert(target == 0); }
        previous = target;
    }
    puts("PASS: low-pedal cutoff, boundary, linear active range and 300 RPM endpoint");
    return 0;
}
