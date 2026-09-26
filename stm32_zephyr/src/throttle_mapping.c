#include "throttle_mapping.h"

uint32_t pedal_target_mrpm(int32_t throttle, int32_t brake)
{
    if (brake != 32767) {
        return 0;
    }
    uint32_t pressed = (uint32_t)(32767 - throttle);
    uint32_t scaled = pressed * THROTTLE_MAX_RPM;
    if (scaled < THROTTLE_MIN_RPM * 65535U) {
        return 0;
    }
    return (uint32_t)((uint64_t)scaled * 1000U / 65535U);
}
