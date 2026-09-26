#ifndef DRIVE_CONTROL_H
#define DRIVE_CONTROL_H

#include <stdbool.h>
#include <stdint.h>
#include "velocity_control.h"

enum drive_mode { DRIVE_COAST, DRIVE_FORWARD, DRIVE_BRAKE };
enum drive_fault { DRIVE_OK, DRIVE_B1_STOP, DRIVE_SENSOR_FAULT, DRIVE_DATA_FAULT };
struct drive_input {
    uint32_t target_mrpm;
    bool linked;
    bool brake;
    bool local_stop;
    bool sensor_fault;
};
struct drive_output {
    enum drive_mode mode;
    float duty_percent; /* Propulsive duty; BRAKE instead uses steady enable high. */
};
struct drive_control {
    struct velocity_control velocity;
    int64_t kick_until_ms;
    int64_t last_ms;
    uint32_t target_mrpm;
    bool running;
    bool initialized;
    enum drive_fault fault;
};

/* Owned only by the main link/motor thread; reset clears latched local faults. */
void drive_init(struct drive_control *control);
/* One nonblocking update per loop. Counts are raw left-negative/right-positive.
 * STOP/brake/link/fault decisions precede PID and override the startup kick. */
struct drive_output drive_step(struct drive_control *control, struct drive_input input,
                               int32_t left, int32_t right, int64_t now_ms);

#endif
