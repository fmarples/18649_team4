#ifndef ACTUATOR_POLICY_H
#define ACTUATOR_POLICY_H
#include "drive_control.h"

/* Preserve main's wire values; the steering bench previously used 5 for self-test. */
enum vehicle_state {
    WAITING = 0, LINK_OK = 1, TIMEOUT = 2, BAD_INPUT = 3, RX_OVERFLOW = 4,
    MOTOR_FAULT = 5, SELF_TEST = 6, ACTUATOR_FAULT = 7
};

struct actuator_policy {
    enum vehicle_state reported_state;
    struct drive_input drive;
    bool linked;
    bool inhibit_servo;
    bool hazards;
};

struct actuator_policy actuator_policy_evaluate(enum vehicle_state link_state,
    bool motor_fault, bool actuator_fault, bool self_test, int32_t brake,
    uint32_t target_mrpm);
#endif
