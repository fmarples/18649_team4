#include <zephyr/ztest.h>
#include "self_test.h"
#include "blinker_core.h"

static struct self_test s;
static void reset(void *unused) { ARG_UNUSED(unused); self_test_reset(&s); }
ZTEST(self_test, test_first_press_is_immediate_and_latched)
{
	self_test_input(&s, 0, SELF_TEST_BUTTON);
	zassert_true(s.active);
	self_test_input(&s, 100, 0);
	self_test_input(&s, 2000, 0);
	zassert_true(s.active);
}
ZTEST(self_test, test_double_press_and_hold)
{
	self_test_input(&s, 0, SELF_TEST_BUTTON);
	self_test_input(&s, 100, SELF_TEST_BUTTON);
	zassert_true(s.active);
	self_test_input(&s, 120, 0);
	self_test_input(&s, 200, SELF_TEST_BUTTON);
	zassert_false(s.active);
	self_test_input(&s, 300, SELF_TEST_BUTTON);
	zassert_false(s.active);
}
ZTEST(self_test, test_fresh_double_press_clears_existing_latch)
{
	self_test_input(&s, 0, SELF_TEST_BUTTON);
	self_test_input(&s, 100, 0);
	self_test_input(&s, 2000, SELF_TEST_BUTTON);
	zassert_true(s.active);
	self_test_input(&s, 2100, 0);
	self_test_input(&s, 2200, SELF_TEST_BUTTON);
	zassert_false(s.active);
}
ZTEST(self_test, test_slow_presses_do_not_clear)
{
	self_test_input(&s, 0, SELF_TEST_BUTTON);
	self_test_input(&s, 100, 0);
	self_test_input(&s, 401, SELF_TEST_BUTTON);
	zassert_true(s.active);
}
ZTEST(self_test, test_short_release_bounce_does_not_clear)
{
	self_test_input(&s, 0, SELF_TEST_BUTTON);
	self_test_input(&s, 5, 0);
	self_test_input(&s, 10, SELF_TEST_BUTTON);
	zassert_true(s.active);
	self_test_input(&s, 30, 0);
	self_test_input(&s, 50, SELF_TEST_BUTTON);
	zassert_false(s.active);
}
ZTEST(self_test, test_paddles_do_not_trigger_self_test)
{
	self_test_input(&s, 0, BLINK_LEFT_BUTTON | BLINK_RIGHT_BUTTON);
	zassert_false(s.active);
}
ZTEST(self_test, test_startup_fault_and_link_fault_override_clear)
{
	zassert_true(self_test_fault(&s, false));
	zassert_false(self_test_fault(&s, true));
	self_test_input(&s, 0, SELF_TEST_BUTTON);
	zassert_true(self_test_fault(&s, true));
	self_test_input(&s, 100, 0);
	self_test_input(&s, 200, SELF_TEST_BUTTON);
	zassert_false(s.active);
	zassert_true(self_test_fault(&s, false));
}
ZTEST(self_test, test_hazards_start_on_boot_and_do_not_restore_old_turn)
{
	struct blinker b;
	blinker_reset(&b);
	struct blink_output o = blinker_step(&b, 0, false, self_test_fault(&s, false), 0, 0);
	zassert_true(o.left && o.right);
	o = blinker_step(&b, 100, true, self_test_fault(&s, true), 0, 0);
	zassert_false(o.left || o.right);
	blinker_step(&b, 120, true, false, BLINK_LEFT_BUTTON, 0);
	self_test_input(&s, 150, SELF_TEST_BUTTON);
	o = blinker_step(&b, 150, true, self_test_fault(&s, true), 0, 0);
	zassert_true(o.left && o.right);
	self_test_input(&s, 250, 0);
	self_test_input(&s, 350, SELF_TEST_BUTTON);
	o = blinker_step(&b, 350, true, self_test_fault(&s, true), 0, 0);
	zassert_false(o.left || o.right);
}
ZTEST_SUITE(self_test, NULL, NULL, reset, NULL, NULL);
