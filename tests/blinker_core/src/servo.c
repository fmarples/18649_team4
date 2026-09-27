#include <zephyr/ztest.h>
#include "servo_core.h"
static struct servo_control s;
static void reset(void *unused) { ARG_UNUSED(unused); servo_reset(&s); }
static void calibration(bool reverse)
{
 s.left = reverse ? 1850 : 1100; s.center = 1510;
 s.right = reverse ? 1100 : 1850; s.marks = 7;
}
ZTEST(servo, test_startup_and_arm)
{
 zassert_equal(s.mode, SERVO_OFF); zassert_equal(s.pulse, 0);
 zassert_false(servo_arm(&s, 0, true));
 zassert_true(servo_arm(&s, 100, false)); zassert_equal(s.pulse, 1500);
 zassert_false(servo_arm(&s, 200, false));
}
ZTEST(servo, test_bounded_steps_and_mode_guard)
{
 zassert_false(servo_step(&s, 25)); servo_arm(&s, 0, false);
 zassert_false(servo_step(&s, 100)); zassert_true(servo_step(&s, -5));
 zassert_equal(s.pulse, 1495);
 s.pulse = 500; zassert_false(servo_step(&s, -5));
 s.pulse = 2500; zassert_false(servo_step(&s, 25));
 s.mode = SERVO_LIVE; zassert_false(servo_step(&s, -25));
}
ZTEST(servo, test_invalid_calibration_and_marks)
{
 zassert_false(servo_mark(&s, 1)); servo_arm(&s, 0, false);
 zassert_true(servo_mark(&s, 2)); zassert_false(servo_cal_valid(&s));
 calibration(false); zassert_true(servo_cal_valid(&s));
 s.center = s.left; zassert_false(servo_cal_valid(&s));
 s.center = 499; zassert_false(servo_cal_valid(&s));
 s.center = 1900; zassert_false(servo_cal_valid(&s));
 zassert_equal(servo_map(&s, 0), 0);
}
ZTEST(servo, test_full_range_monotonic_both_orientations)
{
 for (int reverse = 0; reverse < 2; reverse++) {
  calibration(reverse); int previous = s.left;
  zassert_equal(servo_map(&s, -32768), s.left);
  zassert_equal(servo_map(&s, 0), s.center);
  zassert_equal(servo_map(&s, 32767), s.right);
  for (int raw = -32768; raw <= 32767; raw++) {
   int mapped = servo_map(&s, raw);
   zassert_true(reverse ? mapped <= previous : mapped >= previous);
   zassert_true(mapped >= 1100 && mapped <= 1850); previous = mapped;
  }
  zassert_equal(servo_map(&s, -32769), 0);
  zassert_equal(servo_map(&s, 32768), 0);
 }
}
ZTEST(servo, test_live_interlocks)
{
 zassert_false(servo_live(&s, true, false, 0));
 servo_arm(&s, 0, false); zassert_false(servo_live(&s, true, false, 0));
 calibration(false);
 zassert_false(servo_live(&s, false, false, 0));
 zassert_false(servo_live(&s, true, true, 0));
 zassert_false(servo_live(&s, true, false, -2001));
 zassert_false(servo_live(&s, true, false, 2001));
 zassert_true(servo_live(&s, true, false, 0)); zassert_equal(s.pulse, s.center);
}
ZTEST(servo, test_lease_disables_and_does_not_auto_resume)
{
 servo_arm(&s, 100, false);
 servo_tick(&s, 599, false, false, 0); zassert_equal(s.mode, SERVO_MANUAL);
 servo_tick(&s, 600, false, false, 0); zassert_equal(s.mode, SERVO_OFF);
 s.heartbeat_ms = 601; servo_tick(&s, 601, true, false, 0);
 zassert_equal(s.mode, SERVO_OFF); zassert_equal(s.pulse, 0);
}
ZTEST(servo, test_live_link_fault_and_self_test)
{
 calibration(false); servo_arm(&s, 0, false); servo_live(&s, true, false, 0);
 servo_tick(&s, 10, true, false, -32768); zassert_equal(s.pulse, s.left);
 servo_tick(&s, 11, false, false, 0); zassert_equal(s.mode, SERVO_OFF);
 servo_arm(&s, 12, false);
 servo_tick(&s, 13, false, true, 0); zassert_equal(s.mode, SERVO_OFF);
 servo_arm(&s, 14, false); servo_live(&s, true, false, 0);
 servo_tick(&s, 15, true, false, INT32_MAX); zassert_equal(s.mode, SERVO_OFF);
}
ZTEST_SUITE(servo, NULL, NULL, reset, NULL, NULL);
