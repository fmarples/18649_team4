#include "bench_control.h"
#include <string.h>

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
        (control->phase != BENCH_IDLE && now_ms >= control->deadline_ms)) {
        disarm(control);
    }
    for (unsigned i = 0; i < 2; ++i) {
        if (powered(control, i) && now_ms - control->progress_ms[i] >= BENCH_STALL_MS) {
            trip(control, i == 0 ? BENCH_LEFT_STALL : BENCH_RIGHT_STALL);
            break;
        }
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
        if (!powered(control, i)) {
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
}

bool bench_command(struct bench_control *control, const char *command, int64_t now_ms)
{
    (void)bench_tick(control, now_ms);
    if (strcmp(command, "STOP") == 0) {
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
    if (control->phase == BENCH_ARMED &&
        (strcmp(command, "LEFT") == 0 || strcmp(command, "RIGHT") == 0 ||
         strcmp(command, "BOTH") == 0 || hold_left || hold_right || hold_both)) {
        control->phase = (strcmp(command, "LEFT") == 0 || hold_left) ? BENCH_LEFT :
                         (strcmp(command, "RIGHT") == 0 || hold_right) ? BENCH_RIGHT : BENCH_BOTH;
        control->hold_test = hold_left || hold_right || hold_both;
        control->hold_at_ms = now_ms + BENCH_PULSE_MS;
        control->deadline_ms = control->hold_at_ms + (control->hold_test ? BENCH_HOLD_MS : 0);
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
