/* Behavior of the forward bench command/output interface; no hardware/mocks. */
#include <assert.h>
#include <stdio.h>
#include "bench_control.h"

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
    expect_output(&control, 1100, 100, 100);
    /* Independent simulated input: both encoders advance forward every 50 ms. */
    for (int64_t now = 1150; now < 6100; now += 50) {
        bench_encoder_update(&control, -(int32_t)(now - 1100),
                             (int32_t)(now - 1100), now);
        expect_output(&control, now, 100, 100);
    }
    expect_output(&control, 6099, 100, 100);
    expect_output(&control, 6100, 0, 0);
    assert(!bench_command(&control, "BOTH", 6101));
    puts("PASS: explicit BOTH command enables both for 5000 ms, then disarms");
}

static void test_commands(void)
{
    struct bench_control control;
    bench_init(&control);
    assert(bench_command(&control, "ARM", 1000));
    assert(bench_command(&control, "LEFT", 1100));
    expect_output(&control, 1100, 100, 0);
    assert(bench_command(&control, "STOP", 1101));
    expect_output(&control, 1101, 0, 0);
    assert(bench_command(&control, "ARM", 1200));
    assert(bench_command(&control, "RIGHT", 1201));
    expect_output(&control, 1201, 0, 100);
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
    expect_output(&control, 1249, 100, 100);
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
    bench_encoder_update(&control, -104, 204, 1200);
    expect_output(&control, 1349, 100, 100);
    expect_output(&control, 1350, 0, 0);

    bench_init(&control);
    assert(bench_command(&control, "ARM", 1000));
    assert(bench_command(&control, "BOTH", 1100));
    bench_encoder_update(&control, -1, 1, 1150);
    bench_encoder_update(&control, -2, 2, 1200);
    bench_encoder_update(&control, -3, 3, 1240);
    expect_output(&control, 1250, 0, 0); /* tiny jitter cannot keep outputs enabled */
    puts("PASS: either wheel stalls/reverses => BOTH off; per-wheel baselines and progress threshold");
}

int main(void)
{
    test_stall_cutoff();
    test_independent_wheel_guards();
    test_both_deadline();
    test_commands();
    return 0;
}
