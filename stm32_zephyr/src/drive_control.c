#include "drive_control.h"
#include "throttle_mapping.h"

void drive_init(struct drive_control *control)
{
    *control = (struct drive_control){0};
}

struct drive_output drive_step(struct drive_control *control, struct drive_input input,
                               int32_t left, int32_t right, int64_t now_ms)
{
    if (control->fault == DRIVE_OK) {
        if (input.local_stop) { control->fault = DRIVE_B1_STOP; }
        else if (input.sensor_fault) { control->fault = DRIVE_SENSOR_FAULT; }
        else if (now_ms < 0 || (control->initialized && now_ms < control->last_ms) ||
                 input.target_mrpm > THROTTLE_MAX_RPM * 1000U ||
                 (input.target_mrpm && input.target_mrpm < THROTTLE_MIN_RPM * 1000U)) {
            control->fault = DRIVE_DATA_FAULT;
        }
    }
    if (!control->initialized && now_ms >= 0) {
        velocity_init(&control->velocity, left, right, now_ms);
    }
    control->last_ms = now_ms;
    control->initialized = true;
    if (control->fault != DRIVE_OK || !input.linked || input.brake || !input.target_mrpm) {
        control->running = false;
        control->target_mrpm = 0;
        /* Observe coast-down/braking without requesting propulsion. The positive
         * argument is unused by PID when regulate=false. Invalid sensors/time
         * must not contaminate the last valid measurement. */
        if ((control->fault == DRIVE_OK || control->fault == DRIVE_B1_STOP) &&
            velocity_update(&control->velocity, left, right, now_ms, 1.0f, false) < 0) {
            control->fault = DRIVE_DATA_FAULT;
        }
        enum drive_mode mode = control->fault == DRIVE_OK && (!input.linked || input.brake) ?
            DRIVE_BRAKE : DRIVE_COAST;
        return (struct drive_output){mode, 0};
    }
    if (!control->running) {
        velocity_init(&control->velocity, left, right, now_ms);
        control->kick_until_ms = now_ms + 200;
        control->running = true;
    }
    bool changed = control->target_mrpm != input.target_mrpm;
    control->target_mrpm = input.target_mrpm;
    bool regulate = now_ms >= control->kick_until_ms;
    int ret = 0;
    if (changed && regulate && control->velocity.regulating) {
        ret = velocity_retarget(&control->velocity, input.target_mrpm / 1000.0f);
    }
    if (ret >= 0) {
        ret = velocity_update(&control->velocity, left, right, now_ms,
                              input.target_mrpm / 1000.0f, regulate);
    }
    if (ret >= 0 && regulate && !control->velocity.regulating) {
        /* End the kick at its deadline, even between encoder updates. Start
         * from the latest measurement without fabricating a sample interval. */
        ret = velocity_retarget(&control->velocity, input.target_mrpm / 1000.0f);
        control->velocity.regulating = ret == 0;
    }
    if (ret < 0) {
        control->running = false;
        control->target_mrpm = 0;
        control->fault = DRIVE_DATA_FAULT;
        return (struct drive_output){DRIVE_COAST, 0};
    }
    float duty = regulate && control->velocity.regulating ?
        control->velocity.command[0] : VELOCITY_START_DUTY;
    return (struct drive_output){DRIVE_FORWARD, duty};
}
