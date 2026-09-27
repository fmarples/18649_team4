/* Exercise production steering and lamp state machines without hardware. */
#include <assert.h>
#include <stdio.h>
#include "servo_core.h"
#include "blinker_core.h"

static struct servo_control calibrated(void)
{
    return (struct servo_control){ .left = 1200, .center = 1600, .right = 2000, .marks = 7 };
}

static void live_does_not_need_usb(void)
{
    struct servo_control s = calibrated();
    assert(servo_arm(&s, 0, false));
    assert(servo_live(&s, true, false, 0));
    servo_tick(&s, 10000, true, false, 32767);
    assert(s.mode == SERVO_LIVE);
    assert(s.pulse == 2000);
}

static void startup_waits_for_link_and_center(void)
{
    struct servo_control s = calibrated();
    assert(servo_auto(&s));
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 10000, false, false, 0);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 10001, true, false, 2001);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 10002, true, false, -2001);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 10003, true, true, 0);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 10004, true, false, 0);
    assert(s.mode == SERVO_LIVE && s.pulse == 1600);
    servo_tick(&s, 20000, true, false, -32768);
    assert(s.mode == SERVO_LIVE && s.pulse == 1200);
    s = (struct servo_control){0};
    assert(!servo_auto(&s));
    assert(s.mode == SERVO_OFF && s.pulse == 0);
}

static void recovery_requires_center(void)
{
    struct servo_control s = calibrated();
    assert(servo_auto(&s));
    servo_tick(&s, 0, true, false, 0);
    servo_tick(&s, 1, false, false, 32767);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 2, true, false, 32767);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 3, true, false, 0);
    assert(s.mode == SERVO_LIVE);
    servo_tick(&s, 4, true, true, 0);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 5, true, false, -32768);
    assert(s.mode == SERVO_WAIT_CENTER);
    servo_tick(&s, 6, true, false, 0);
    assert(s.mode == SERVO_LIVE);
    servo_tick(&s, 7, true, false, INT32_MAX);
    assert(s.mode == SERVO_WAIT_CENTER && s.pulse == 0);
    servo_tick(&s, 8, true, false, 32767);
    assert(s.mode == SERVO_WAIT_CENTER);
}

static void manual_and_explicit_off_still_stop(void)
{
    struct servo_control s = calibrated();
    assert(servo_arm(&s, 100, false));
    servo_tick(&s, 599, false, false, 0);
    assert(s.mode == SERVO_MANUAL);
    servo_tick(&s, 600, true, false, 0);
    assert(s.mode == SERVO_OFF && s.pulse == 0);
    servo_tick(&s, 10000, true, false, 0);
    assert(s.mode == SERVO_OFF && s.pulse == 0);
}

static void blinkers_and_steering_run_together(void)
{
    struct servo_control s = calibrated();
    struct blinker b;
    blinker_reset(&b);
    assert(servo_auto(&s));
    servo_tick(&s, 10000, true, false, 0);
    struct blink_output lamps = blinker_step(&b, 10000, true, false, 1U << 5, 0);
    assert(lamps.left && !lamps.right);
    servo_tick(&s, 10020, true, false, -32768);
    lamps = blinker_step(&b, 10020, true, false, 0, -32768);
    assert(s.pulse == 1200 && lamps.left && !lamps.right);
    servo_tick(&s, 10100, true, false, 0);
    lamps = blinker_step(&b, 10100, true, false, 0, 0);
    assert(s.pulse == 1600 && !lamps.left && !lamps.right);
}

int main(void)
{
    live_does_not_need_usb();
    startup_waits_for_link_and_center();
    recovery_requires_center();
    manual_and_explicit_off_still_stop();
    blinkers_and_steering_run_together();
    puts("PASS: standalone servo contracts");
    return 0;
}
