#include <zephyr/ztest.h>
#include "blinker_core.h"

static struct blinker b;
static void reset(void *unused) { ARG_UNUSED(unused); blinker_reset(&b); }
static struct blink_output step(uint64_t ms, uint32_t buttons, int32_t steer)
{ return blinker_step(&b, ms, true, false, buttons, steer); }
static void expect(struct blink_output o, bool l, bool r)
{ zassert_equal(o.left, l); zassert_equal(o.right, r); }

ZTEST(blinkers, test_waiting_and_neutral_are_off)
{
	expect(blinker_step(&b, 0, false, false, 0, 0), false, false);
	expect(step(1000, 0, 0), false, false);
}
ZTEST(blinkers, test_left_phase_boundaries)
{
	expect(step(100, BLINK_LEFT_BUTTON, 0), true, false);
	expect(step(599, 0, 0), true, false);
	expect(step(600, 0, 0), false, false);
	expect(step(1099, 0, 0), false, false);
	expect(step(1100, 0, 0), true, false);
}
ZTEST(blinkers, test_late_service_does_not_accumulate_drift)
{
	step(0, BLINK_LEFT_BUTTON, 0);
	expect(step(570, 0, 0), false, false);
	expect(step(1000, 0, 0), true, false);
	expect(step(1500, 0, 0), false, false);
	expect(step(10000500, 0, 0), false, false);
}
ZTEST(blinkers, test_right_and_switch_reset_turn_history)
{
	step(0, BLINK_RIGHT_BUTTON, 12000);
	zassert_true(b.crossed_turn);
	step(10, 0, 12000);
	expect(step(20, BLINK_LEFT_BUTTON, 12000), true, false);
	zassert_false(b.crossed_turn);
	step(30, 0, 0);
	zassert_equal(b.mode, BLINK_LEFT);
}
ZTEST(blinkers, test_repeat_press_cancels_but_held_button_does_not)
{
	step(0, BLINK_LEFT_BUTTON, 0);
	step(10, BLINK_LEFT_BUTTON, 0);
	zassert_equal(b.mode, BLINK_LEFT);
	step(20, 0, 0);
	expect(step(30, BLINK_LEFT_BUTTON, 0), false, false);
}
ZTEST(blinkers, test_left_turn_hysteresis_and_held_self_cancel)
{
	step(0, BLINK_LEFT_BUTTON, 0);
	step(10, BLINK_LEFT_BUTTON, -7999);
	step(20, BLINK_LEFT_BUTTON, 0);
	zassert_equal(b.mode, BLINK_LEFT);
	step(30, BLINK_LEFT_BUTTON, -8000);
	zassert_true(b.crossed_turn);
	step(40, BLINK_LEFT_BUTTON, -6001);
	zassert_equal(b.mode, BLINK_LEFT);
	expect(step(50, BLINK_LEFT_BUTTON, -6000), false, false);
	step(60, BLINK_LEFT_BUTTON, -12000);
	zassert_equal(b.mode, BLINK_OFF);
}
ZTEST(blinkers, test_right_self_cancel_and_wrong_direction)
{
	step(0, BLINK_RIGHT_BUTTON, -20000);
	step(10, 0, 0);
	zassert_false(b.crossed_turn);
	zassert_equal(b.mode, BLINK_RIGHT);
	step(20, 0, 8000);
	expect(step(30, 0, 6000), false, false);
}
ZTEST(blinkers, test_simultaneous_buttons_cancel)
{
	step(0, 0, 0);
	expect(step(1, BLINK_LEFT_BUTTON | BLINK_RIGHT_BUTTON, 0), false, false);
	expect(step(2, BLINK_RIGHT_BUTTON, 0), false, false);
	step(3, 0, 0);
	expect(step(4, BLINK_RIGHT_BUTTON, 0), false, true);
}
ZTEST(blinkers, test_new_opposite_press_wins_over_held_paddle)
{
	step(0, BLINK_LEFT_BUTTON, 0);
	expect(step(10, BLINK_LEFT_BUTTON | BLINK_RIGHT_BUTTON, 0), false, true);
	expect(step(20, BLINK_LEFT_BUTTON | BLINK_RIGHT_BUTTON, 0), false, true);
}
ZTEST(blinkers, test_fault_priority_and_hazard_frequency)
{
	step(0, BLINK_LEFT_BUTTON, 0);
	expect(blinker_step(&b, 100, false, true, BLINK_RIGHT_BUTTON, 9000), true, true);
	expect(blinker_step(&b, 349, false, true, 0, 0), true, true);
	expect(blinker_step(&b, 350, false, true, BLINK_LEFT_BUTTON, 0), false, false);
	expect(blinker_step(&b, 600, false, true, 0, 0), true, true);
}
ZTEST(blinkers, test_recovery_does_not_restore_old_or_held_turn)
{
	step(0, BLINK_RIGHT_BUTTON, 9000);
	blinker_step(&b, 10, false, true, 0, 0);
	expect(step(20, BLINK_LEFT_BUTTON, 0), false, false);
	expect(step(30, BLINK_LEFT_BUTTON, 0), false, false);
	step(40, 0, 0);
	expect(step(50, BLINK_LEFT_BUTTON, 0), true, false);
}
ZTEST(blinkers, test_other_buttons_and_long_uptime)
{
	uint64_t start = (1ULL << 32) - 100;
	expect(step(start, BLINK_RIGHT_BUTTON | 1, 0), false, true);
	expect(step(start + 500, 1, 0), false, false);
	expect(step(start + 1000, 1, 0), false, true);
}
ZTEST_SUITE(blinkers, NULL, NULL, reset, NULL, NULL);
