#include "actuator_policy.h"

struct actuator_policy actuator_policy_evaluate(enum vehicle_state link_state,
    bool motor_fault, bool actuator_fault, bool self_test, int32_t brake,
    uint32_t target_mrpm)
{
    bool linked = link_state == LINK_OK && !motor_fault && !actuator_fault;
    return (struct actuator_policy){
        .reported_state = motor_fault ? MOTOR_FAULT : actuator_fault ? ACTUATOR_FAULT :
            link_state != LINK_OK ? link_state : self_test ? SELF_TEST : LINK_OK,
        .drive = {
            .linked = linked,
            .brake = self_test || brake != 32767,
            .target_mrpm = linked && !self_test && brake == 32767 ? target_mrpm : 0,
        },
        .linked = linked,
        /* Manual bench calibration can still run without a Pi; LIVE cannot. */
        .inhibit_servo = motor_fault || actuator_fault || self_test,
        .hazards = !linked || self_test,
    };
}
