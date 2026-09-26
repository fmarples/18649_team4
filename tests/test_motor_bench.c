/* Behavior of the forward bench command/output interface; no hardware/mocks. */
#include <assert.h>
#include <stdio.h>
#include "bench_control.h"

#ifndef EXPECTED_DUTY
#define EXPECTED_DUTY 60
#endif

static void expect_output(struct bench_control *control, int64_t now,
                          unsigned left, unsigned right)
{
    struct bench_output out = bench_tick(control, now);
    assert(out.left_percent == left && out.right_percent == right);
}

static void test_both_deadline(void)
{
    struct bench_control control;
    bench_init(&control);
    expect_output(&control, 0, 0, 0);
    assert(!bench_command(&control, "BOTH", 0));
    assert(bench_command(&control, "ARM", 1000));
    expect_output(&control, 1001, 0, 0);
    assert(bench_command(&control, "BOTH", 1100));
    expect_output(&control, 1100, EXPECTED_DUTY, EXPECTED_DUTY);
    /* Independent simulated input: both encoders advance forward every 50 ms. */
    for (int64_t now = 1150; now < 1300; now += 50) {
        bench_encoder_update(&control, -(int32_t)(now - 1100),
                             (int32_t)(now - 1100), now);
        expect_output(&control, now, EXPECTED_DUTY, EXPECTED_DUTY);
    }
    expect_output(&control, 1299, EXPECTED_DUTY, EXPECTED_DUTY);
    expect_output(&control, 1300, 0, 0);
    assert(!bench_command(&control, "BOTH", 1301));
    puts("PASS: explicit BOTH command enables both for 200 ms, then disarms");
}

static void test_commands(void)
{
    struct bench_control control;
    bench_init(&control);
    assert(bench_command(&control, "ARM", 1000));
    assert(bench_command(&control, "LEFT", 1100));
    expect_output(&control, 1100, EXPECTED_DUTY, 0);
    assert(bench_command(&control, "STOP", 1101));
    expect_output(&control, 1101, 0, 0);
    assert(bench_command(&control, "ARM", 1200));
    assert(bench_command(&control, "RIGHT", 1201));
    expect_output(&control, 1201, 0, EXPECTED_DUTY);
    assert(!bench_command(&control, "BOTH", 1202)); /* no switching/retrigger */
    expect_output(&control, 1202, 0, 0);
    assert(bench_command(&control, "ARM", 1300));
    assert(!bench_command(&control, "BOTH", 6300)); /* arm expires */
    assert(bench_command(&control, "ARM", 7000));
    assert(!bench_command(&control, "BOTH 100", 7001));
    expect_output(&control, 7001, 0, 0);
    assert(bench_command(&control, "ARM", 7100));
    assert(bench_command(&control, "BOTH", 7101));
    assert(!bench_command(&control, "BOTH", 7102));
    expect_output(&control, 7102, 0, 0);
    puts("PASS: selected channels, STOP, arm expiry, invalid commands and no retrigger");
}

static void test_stall_cutoff(void)
{
    struct bench_control control;
    bench_init(&control);
    assert(bench_command(&control, "ARM", 1000));
    assert(bench_command(&control, "BOTH", 1100));
    expect_output(&control, 1249, EXPECTED_DUTY, EXPECTED_DUTY);
    expect_output(&control, 1250, 0, 0); /* neither encoder has progressed */
    assert(!bench_command(&control, "ARM", 1251));
    assert(bench_command(&control, "STOP", 1252));
    assert(!bench_command(&control, "ARM", 1253)); /* fault stays latched */
    puts("PASS: no encoder progress stops BOTH at 150 ms and blocks rearming");
}

static void test_independent_wheel_guards(void)
{
    struct bench_control control;
    for (unsigned stalled = 0; stalled < 2; ++stalled) {
        bench_init(&control);
        assert(bench_command(&control, "ARM", 1000));
        assert(bench_command(&control, "BOTH", 1100));
        bench_encoder_update(&control, stalled == 0 ? 0 : -10,
                             stalled == 1 ? 0 : 10, 1140);
        bench_encoder_update(&control, stalled == 0 ? 0 : -20,
                             stalled == 1 ? 0 : 20, 1240);
        expect_output(&control, 1250, 0, 0);
        assert(control.fault == (stalled == 0 ? BENCH_LEFT_STALL : BENCH_RIGHT_STALL));
    }
    for (unsigned reversed = 0; reversed < 2; ++reversed) {
        bench_init(&control);
        assert(bench_command(&control, "ARM", 1000));
        assert(bench_command(&control, "BOTH", 1100));
        bench_encoder_update(&control, reversed == 0 ? 4 : -4,
                             reversed == 1 ? -4 : 4, 1110);
        expect_output(&control, 1110, 0, 0);
        assert(control.fault == (reversed == 0 ? BENCH_LEFT_REVERSED : BENCH_RIGHT_REVERSED));
    }
    bench_init(&control);
    bench_encoder_update(&control, -100, 200, 900); /* nonzero boot/baseline counts */
    assert(bench_command(&control, "ARM", 1000));
    assert(bench_command(&control, "BOTH", 1100));
    bench_encoder_update(&control, -104, 204, 1140);
    expect_output(&control, 1289, EXPECTED_DUTY, EXPECTED_DUTY);
    expect_output(&control, 1290, 0, 0);

    bench_init(&control);
    assert(bench_command(&control, "ARM", 1000));
    assert(bench_command(&control, "BOTH", 1100));
    bench_encoder_update(&control, -1, 1, 1150);
    bench_encoder_update(&control, -2, 2, 1200);
    bench_encoder_update(&control, -3, 3, 1240);
    expect_output(&control, 1250, 0, 0); /* tiny jitter cannot keep outputs enabled */
    puts("PASS: either wheel stalls/reverses => BOTH off; per-wheel baselines and progress threshold");
}

/* HOLD commands preserve the kick, then hold one wheel with the same guards. */
static void test_kick_then_hold(void)
{
#ifndef EXPECTED_HOLD
#define EXPECTED_HOLD 55
#endif
#ifndef EXPECTED_HOLD_MS
#define EXPECTED_HOLD_MS 2000
#endif
    const int64_t deadline = 1300 + EXPECTED_HOLD_MS;
    const char *commands[] = {"HOLDLEFT", "HOLDRIGHT"};
    for (unsigned wheel = 0; wheel < 2; ++wheel) {
        struct bench_control control;
        bench_init(&control);
        assert(!bench_command(&control, commands[wheel], 0));
        assert(bench_command(&control, "ARM", 1000));
        assert(bench_command(&control, commands[wheel], 1100));
        expect_output(&control, 1100, wheel == 0 ? 60 : 0, wheel == 1 ? 60 : 0);
        for (int64_t now = 1150; now < deadline; now += 50) {
            bench_encoder_update(&control, wheel == 0 ? -(int32_t)now : 0,
                                 wheel == 1 ? (int32_t)now : 0, now);
            unsigned duty = now < 1300 ? 60 : EXPECTED_HOLD;
            expect_output(&control, now, wheel == 0 ? duty : 0, wheel == 1 ? duty : 0);
        }
        expect_output(&control, deadline - 1, wheel == 0 ? EXPECTED_HOLD : 0,
                      wheel == 1 ? EXPECTED_HOLD : 0);
        expect_output(&control, deadline, 0, 0);
        assert(!bench_command(&control, commands[wheel], deadline + 1));

        bench_init(&control);
        assert(bench_command(&control, "ARM", 0));
        assert(bench_command(&control, commands[wheel], 0));
        bench_encoder_update(&control, wheel == 0 ? -10 : 0,
                             wheel == 1 ? 10 : 0, 100);
        expect_output(&control, 249, wheel == 0 ? EXPECTED_HOLD : 0,
                      wheel == 1 ? EXPECTED_HOLD : 0);
        expect_output(&control, 250, 0, 0); /* Transition does not reset progress timer. */
        assert(control.fault == (wheel == 0 ? BENCH_LEFT_STALL : BENCH_RIGHT_STALL));
        assert(!bench_command(&control, "ARM", 251));
    }
    struct bench_control control;
    bench_init(&control);
    assert(bench_command(&control, "ARM", 0));
    assert(!bench_command(&control, "HOLDBOTH 40", 1));
    expect_output(&control, 1, 0, 0);
    assert(bench_command(&control, "ARM", 2));
    assert(bench_command(&control, "HOLDLEFT", 3));
    assert(bench_command(&control, "STOP", 4));
    expect_output(&control, 4, 0, 0);
    assert(bench_command(&control, "ARM", 5));
    assert(bench_command(&control, "HOLDLEFT", 6));
    assert(!bench_command(&control, "HOLDRIGHT", 7));
    expect_output(&control, 7, 0, 0);
    puts("PASS: isolated 60%/200ms kick + fixed-duty/bounded hold; cutoff/STOP/retrigger");
}

/* Both wheels get the same stage duty; either wheel's guard disables both. */
static void test_hold_both(void)
{
    struct bench_control control;
    bench_init(&control);
    assert(!bench_command(&control, "HOLDBOTH", 0));
    assert(bench_command(&control, "ARM", 0));
    assert(bench_command(&control, "HOLDBOTH", 100));
    expect_output(&control, 100, 60, 60);
    for (int64_t now = 150; now < 300 + EXPECTED_HOLD_MS; now += 50) {
        bench_encoder_update(&control, -(int32_t)now, (int32_t)now, now);
        unsigned duty = now < 300 ? 60 : EXPECTED_HOLD;
        expect_output(&control, now, duty, duty);
    }
    expect_output(&control, 300 + EXPECTED_HOLD_MS, 0, 0);
    for (unsigned wheel = 0; wheel < 2; ++wheel) {
        bench_init(&control);
        assert(bench_command(&control, "ARM", 0));
        assert(bench_command(&control, "HOLDBOTH", 0));
        bench_encoder_update(&control, -10, 10, 100);
        bench_encoder_update(&control, wheel == 0 ? -10 : -20,
                             wheel == 1 ? 10 : 20, 200);
        expect_output(&control, 249, EXPECTED_HOLD, EXPECTED_HOLD);
        expect_output(&control, 250, 0, 0);
        assert(control.fault == (wheel == 0 ? BENCH_LEFT_STALL : BENCH_RIGHT_STALL));
        assert(!bench_command(&control, "ARM", 251));
    }
    puts("PASS: HOLDBOTH stage transition, deadline and either-wheel cutoff");
}

int main(void)
{
    test_hold_both();
    test_kick_then_hold();
    test_stall_cutoff();
    test_independent_wheel_guards();
    test_both_deadline();
    test_commands();
    return 0;
}
