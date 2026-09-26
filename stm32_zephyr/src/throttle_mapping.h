#ifndef THROTTLE_MAPPING_H
#define THROTTLE_MAPPING_H

#include <stdint.h>

/* Mean of the three simultaneous 40%-duty holds in MOTOR_CHARACTERIZATION.md.
 * This is an initial measured threshold, not a guaranteed loaded minimum. */
#define THROTTLE_MIN_RPM 23U
/* User-selected full-pedal target, distinct from measured full-duty speed. */
#define THROTTLE_MAX_RPM 300U

/* Convert protocol-validated raw pedals (-32768..32767) into milli-RPM.
 * Any brake press wins. Throttle values below the measured sustaining speed
 * request STOP, not a positive target that PID's 40% floor cannot achieve.
 * The motor owner must apply the startup kick only on stopped->driving. */
uint32_t pedal_target_mrpm(int32_t throttle, int32_t brake);

#endif
