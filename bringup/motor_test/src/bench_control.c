#include "bench_control.h"
#include <string.h>
#include <limits.h>

static bool powered(const struct bench_control *control, unsigned wheel)
{
    return control->phase == BENCH_BOTH ||
           control->phase == (wheel == 0 ? BENCH_LEFT : BENCH_RIGHT);
}

static void disarm(struct bench_control *control)
{
    control->phase = BENCH_IDLE;
    control->deadline_ms = 0;
    control->hold_test = false;
    control->pid_test = false;
    control->target_rpm = 0;
    velocity_init(&control->velocity, control->counts[0], control->counts[1], 0);
    control->hold_at_ms = 0;
}

static void trip(struct bench_control *control, enum bench_fault fault)
{
    control->fault = fault;
    disarm(control);
}

void bench_init(struct bench_control *control)
{
    *control = (struct bench_control){.phase = BENCH_IDLE};
}

struct bench_output bench_tick(struct bench_control *control, int64_t now_ms)
{
    if (control->fault != BENCH_OK ||
        (control->phase != BENCH_IDLE && !control->pid_test && now_ms >= control->deadline_ms)) {
        disarm(control);
    }
    for (unsigned i = 0; i < 2; ++i) {
        if (!control->pid_test && powered(control, i) && now_ms - control->progress_ms[i] >= BENCH_STALL_MS) {
            trip(control, i == 0 ? BENCH_LEFT_STALL : BENCH_RIGHT_STALL);
            break;
        }
    }
    if (control->pid_test) {
        if (now_ms < control->hold_at_ms) {
            return (struct bench_output){BENCH_KICK_PERCENT, BENCH_KICK_PERCENT};
        }
        return (struct bench_output){
            control->velocity.regulating ? control->velocity.command[0] : BENCH_KICK_PERCENT,
            control->velocity.regulating ? control->velocity.command[1] : BENCH_KICK_PERCENT,
        };
    }
    unsigned duty = control->hold_test ?
        (now_ms < control->hold_at_ms ? BENCH_KICK_PERCENT : BENCH_HOLD_PERCENT) :
        BENCH_DUTY_PERCENT;
    return (struct bench_output){
        .left_percent = powered(control, 0) ? duty : 0U,
        .right_percent = powered(control, 1) ? duty : 0U,
    };
}

void bench_encoder_update(struct bench_control *control, int32_t left,
                          int32_t right, int64_t now_ms)
{
    (void)bench_tick(control, now_ms);
    int32_t counts[] = {left, right};
    for (unsigned i = 0; i < 2; ++i) {
        control->counts[i] = counts[i];
        /* Manual PID load tests deliberately permit a held/backdriven wheel.
         * Retain motion cutoffs only for the startup/fixed-duty diagnostics. */
        if (!powered(control, i) || control->pid_test) {
            control->anchors[i] = counts[i];
            continue;
        }
        int64_t delta = (int64_t)counts[i] - control->anchors[i];
        int64_t forward = i == 0 ? -delta : delta;
        if (forward <= -BENCH_PROGRESS_COUNTS) {
            trip(control, i == 0 ? BENCH_LEFT_REVERSED : BENCH_RIGHT_REVERSED);
        } else if (forward >= BENCH_PROGRESS_COUNTS) {
            control->anchors[i] = counts[i];
            control->progress_ms[i] = now_ms;
        }
    }
    if (control->pid_test && velocity_update(&control->velocity, left, right,
            now_ms, (float)control->target_rpm, now_ms >= control->hold_at_ms) < 0) {
        trip(control, BENCH_VELOCITY_FAULT);
    }
}

void bench_button_update(struct bench_control *control, bool pressed)
{
    if (pressed && control->fault == BENCH_OK) { trip(control, BENCH_USER_STOP); }
}

bool bench_command(struct bench_control *control, const char *command, int64_t now_ms)
{
    (void)bench_tick(control, now_ms);
    if (strcmp(command, "STOP") == 0 || strcmp(command, "PID 0") == 0) {
        disarm(control);
        return true;
    }
    if (control->fault != BENCH_OK) {
        disarm(control);
        return false;
    }
    if (strcmp(command, "ARM") == 0 && control->phase == BENCH_IDLE) {
        control->phase = BENCH_ARMED;
        control->deadline_ms = now_ms + 5000;
        return true;
    }
    bool hold_left = strcmp(command, "HOLDLEFT") == 0;
    bool hold_right = strcmp(command, "HOLDRIGHT") == 0;
    bool hold_both = strcmp(command, "HOLDBOTH") == 0;
    unsigned target = 0;
    bool pid = strncmp(command, "PID ", 4) == 0 && command[4] != '\0';
    if (pid) {
        for (const char *digit = command + 4; *digit; ++digit) {
            if (*digit < '0' || *digit > '9' || target > (UINT_MAX - (unsigned)(*digit - '0')) / 10U) {
                pid = false;
                break;
            }
            target = target * 10U + (unsigned)(*digit - '0');
        }
    }
    pid = pid && target > 0;
    if (control->phase == BENCH_ARMED &&
        (strcmp(command, "LEFT") == 0 || strcmp(command, "RIGHT") == 0 ||
         strcmp(command, "BOTH") == 0 || hold_left || hold_right || hold_both || pid)) {
        control->phase = (strcmp(command, "LEFT") == 0 || hold_left) ? BENCH_LEFT :
                         (strcmp(command, "RIGHT") == 0 || hold_right) ? BENCH_RIGHT : BENCH_BOTH;
        control->hold_test = hold_left || hold_right || hold_both;
        control->pid_test = pid;
        control->target_rpm = pid ? target : 0;
        if (pid) {
            velocity_init(&control->velocity, control->counts[0], control->counts[1], now_ms);
        }
        control->hold_at_ms = now_ms + BENCH_PULSE_MS;
        control->deadline_ms = pid ? 0 : control->hold_at_ms +
            (control->hold_test ? BENCH_HOLD_MS : 0);
        for (unsigned i = 0; i < 2; ++i) {
            control->anchors[i] = control->counts[i];
            control->progress_ms[i] = now_ms;
        }
        return true;
    }
    /* Malformed, unarmed, duplicate, or retrigger commands disarm and stop. */
    disarm(control);
    return false;
}
