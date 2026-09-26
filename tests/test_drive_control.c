/* Production pedal mapper -> PID/kick/output policy, without hardware mocks. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "drive_control.h"
#include "throttle_mapping.h"

/* Exercise the same validated-pedal input used by the STM32 command owner. */
static struct drive_input pedal(int32_t raw)
{
    return (struct drive_input){.linked = true,
        .target_mrpm = pedal_target_mrpm(raw, 32767)};
}

static void test_pedal_kick_pid(void)
{
    struct drive_control c;
    drive_init(&c);
    struct drive_input input = pedal(32767);
    struct drive_output out = drive_step(&c, input, 0, 0, 0);
    assert(out.mode == DRIVE_COAST && out.duty_percent == 0);
    input = pedal(27743); /* Immediately below the measured cutoff. */
    out = drive_step(&c, input, 0, 0, 10);
    assert(out.mode == DRIVE_COAST && out.duty_percent == 0);
    input = pedal(27742);
    out = drive_step(&c, input, 0, 0, 20);
    assert(out.mode == DRIVE_FORWARD && out.duty_percent == 60);
    for (int64_t t = 40; t < 220; t += 20) {
        /* Incoming pedal updates must not extend the startup kick. */
        input = pedal(t < 100 ? 27742 : 0);
        out = drive_step(&c, input, -(int32_t)t, (int32_t)t, t);
        assert(out.duty_percent == 60);
    }
    out = drive_step(&c, input, -220, 220, 220);
    assert(c.velocity.regulating);
    assert(out.mode == DRIVE_FORWARD && out.duty_percent >= 40 && out.duty_percent <= 100);
    assert(out.duty_percent != 60); /* Changed target did not restart the kick. */
    input = pedal(32767);
    out = drive_step(&c, input, -221, 221, 221);
    assert(out.mode == DRIVE_COAST && out.duty_percent == 0);
    input = pedal(-32768);
    out = drive_step(&c, input, -230, 230, 230);
    assert(out.mode == DRIVE_FORWARD && out.duty_percent == 60);
    out = drive_step(&c, input, -429, 429, 429);
    assert(out.duty_percent == 60);
    out = drive_step(&c, input, -450, 450, 450);
    assert(c.velocity.regulating && out.duty_percent >= 40 && out.duty_percent <= 100);
    puts("PASS: cutoff -> kick -> PID; moving updates preserve kick deadline; every restart kicks");
}

/* Every stop source preempts both the kick and normal running. */
static void test_stop_priority_and_recovery(void)
{
    for (unsigned running = 0; running < 2; ++running) {
        for (unsigned reason = 0; reason < 5; ++reason) {
            struct drive_control c;
            drive_init(&c);
            struct drive_input input = pedal(-32768);
            (void)drive_step(&c, input, 0, 0, 0);
            int64_t now = running ? 250 : 10;
            if (running) { (void)drive_step(&c, input, -250, 250, 250); }
            if (reason == 0) { input.linked = false; }
            if (reason == 1) { input.brake = true; }
            if (reason == 2) { input.local_stop = true; }
            if (reason == 3) { input.sensor_fault = true; }
            if (reason == 4) { input.target_mrpm = 0; }
            struct drive_output out = drive_step(&c, input, -260, 260, now + 1);
            assert(out.duty_percent == 0);
            assert(out.mode == (reason < 2 ? DRIVE_BRAKE : DRIVE_COAST));
            assert(!c.running && c.target_mrpm == 0);
            input = pedal(-32768);
            out = drive_step(&c, input, -270, 270, now + 2);
            if (reason == 2 || reason == 3) {
                assert(out.mode == DRIVE_COAST && out.duty_percent == 0);
                assert(c.fault != DRIVE_OK); /* Fresh packets cannot clear B1/fault. */
            } else {
                assert(out.mode == DRIVE_FORWARD && out.duty_percent == 60);
            }
        }
    }
    struct drive_control c;
    drive_init(&c);
    struct drive_output out = drive_step(&c, (struct drive_input){0}, 0, 0, 0);
    assert(out.mode == DRIVE_BRAKE && out.duty_percent == 0); /* Cold start. */
    puts("PASS: cold-start/link/brake dynamic stop; zero pedal coasts; B1/sensor faults latch");
}

static void test_invalid_data_and_continuous_hold(void)
{
    struct drive_control c;
    drive_init(&c);
    struct drive_input input = pedal(-32768);
    for (int64_t t = 0; t <= 60000; t += 20) {
        struct drive_output out = drive_step(&c, input, 0, 0, t);
        assert(out.mode == DRIVE_FORWARD && out.duty_percent >= 40 && out.duty_percent <= 100);
        assert(c.fault == DRIVE_OK); /* No stall guard or duration cap in PID. */
    }
    struct drive_output out = drive_step(&c, input, 0, 0, 59999);
    assert(out.mode == DRIVE_COAST && c.fault == DRIVE_DATA_FAULT);
    out = drive_step(&c, input, 0, 0, 60001);
    assert(out.mode == DRIVE_COAST);
    drive_init(&c);
    input.target_mrpm = 300001;
    out = drive_step(&c, input, 0, 0, 0);
    assert(out.mode == DRIVE_COAST && c.fault == DRIVE_DATA_FAULT);
    puts("PASS: continuous PID permits stationary encoders; invalid data/time latch off");
}

/* New pedals must affect duty without waiting for the 20 ms encoder period. */
static void test_running_target_changes_immediately(void)
{
    struct drive_control c;
    drive_init(&c);
    struct drive_input input = {.linked = true, .target_mrpm = 100000};
    (void)drive_step(&c, input, 0, 0, 0);
    struct drive_output before = drive_step(&c, input, -220, 220, 200);
    input.target_mrpm = 200000;
    struct drive_output after = drive_step(&c, input, -220, 220, 201);
    assert(fabsf(after.duty_percent - before.duty_percent - 12.0f) < 0.001f);
    assert(c.velocity.sample_ms == 200); /* No invented new encoder interval. */
    puts("PASS: running pedal changes update P/output immediately without a new kick");
}

static void test_kick_deadline_between_encoder_samples(void)
{
    struct drive_control c;
    drive_init(&c);
    struct drive_input input = {.linked = true, .target_mrpm = 23000};
    (void)drive_step(&c, input, 0, 0, 0);
    for (int64_t t = 21; t <= 189; t += 21) {
        struct drive_output out = drive_step(&c, input, -(int32_t)(t * 2), (int32_t)(t * 2), t);
        assert(out.duty_percent == 60 && !c.velocity.regulating);
    }
    struct drive_output out = drive_step(&c, input, -400, 400, 200);
    assert(c.velocity.regulating);
    assert(c.velocity.sample_ms == 189);
    assert(out.duty_percent < 60 && out.duty_percent >= 40);
    puts("PASS: kick ends on the first update at 200 ms, even between encoder samples");
}

int main(void)
{
    test_pedal_kick_pid();
    test_stop_priority_and_recovery();
    test_invalid_data_and_continuous_hold();
    test_running_target_changes_immediately();
    test_kick_deadline_between_encoder_samples();
    return 0;
}
