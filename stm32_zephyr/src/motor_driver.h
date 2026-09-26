#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H

#include "drive_control.h"

struct motor_report {
    int fault;
    enum drive_mode mode;
    uint32_t target_mrpm;
    int32_t left_mrpm, right_mrpm, average_mrpm;
    uint32_t duty_mpercent;
    int32_t left_count, right_count;
    int64_t sample_ms;
};

/* Configure the existing bench pins, encoders and B1; never start propulsion. */
int motor_init(void);
/* Main is the sole motor-output owner. Call at least every ~1 ms, outside the
 * shared-state mutex. This reads encoders/B1, runs PID and writes both bridges.
 * HAL/sensor/B1 failures latch off until reset and are returned in the report. */
struct motor_report motor_update(struct drive_input input);

#endif
