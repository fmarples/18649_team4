#include <zephyr/ztest.h>
#include "actuator_policy.h"
#include "self_test.h"
#include "blinker_core.h"
#include "servo_core.h"
#include "schedule.h"

static struct servo_control calibrated(void)
{
    return (struct servo_control){.left = 1200, .center = 1600, .right = 2000, .marks = 7};
}

ZTEST(actuators, test_startup_and_normal_controls)
{
    struct drive_control motor;
    struct blinker lamps;
    struct servo_control servo = calibrated();
    drive_init(&motor);
    blinker_reset(&lamps);
    struct actuator_policy p = actuator_policy_evaluate(WAITING, false, false, false, 32767, 300000);
    zassert_equal(p.reported_state, WAITING);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 0).mode, DRIVE_BRAKE);
    struct blink_output out = blinker_step(&lamps, 0, p.linked, p.hazards, 0, 0);
    zassert_true(out.left && out.right);
    zassert_equal(servo.mode, SERVO_OFF);
    p = actuator_policy_evaluate(LINK_OK, false, false, false, 32767, 300000);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 1).mode, DRIVE_FORWARD);
    out = blinker_step(&lamps, 1, p.linked, p.hazards, 0, 0);
    zassert_false(out.left || out.right);
    servo_tick(&servo, 1, p.linked, p.inhibit_servo, 0);
    zassert_equal(servo.mode, SERVO_OFF); /* Motor readiness never auto-arms steering. */
}

ZTEST(actuators, test_self_test_brakes_during_kick_and_disables_steering)
{
    struct drive_control motor;
    struct self_test test;
    struct blinker lamps;
    struct servo_control servo = calibrated();
    drive_init(&motor); self_test_reset(&test); blinker_reset(&lamps);
    struct actuator_policy p = actuator_policy_evaluate(LINK_OK, false, false, false, 32767, 300000);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 0).mode, DRIVE_FORWARD);
    zassert_true(servo_arm(&servo, 0, false));
    zassert_true(servo_live(&servo, true, false, 0));
    self_test_input(&test, 10, SELF_TEST_BUTTON);
    p = actuator_policy_evaluate(LINK_OK, false, false, test.active, 32767, 300000);
    zassert_equal(p.reported_state, SELF_TEST);
    zassert_equal(drive_step(&motor, p.drive, -2, 2, 10).mode, DRIVE_BRAKE);
    servo_tick(&servo, 10, p.linked, p.inhibit_servo, 0);
    zassert_equal(servo.mode, SERVO_OFF);
    struct blink_output out = blinker_step(&lamps, 10, p.linked, p.hazards, 0, 0);
    zassert_true(out.left && out.right);
    self_test_input(&test, 40, 0);
    self_test_input(&test, 100, SELF_TEST_BUTTON);
    p = actuator_policy_evaluate(LINK_OK, false, false, test.active, 32767, 300000);
    zassert_equal(p.reported_state, LINK_OK);
    zassert_equal(drive_step(&motor, p.drive, -5, 5, 100).mode, DRIVE_FORWARD);
    servo_tick(&servo, 100, p.linked, p.inhibit_servo, 0);
    zassert_equal(servo.mode, SERVO_OFF); /* Recovery still requires explicit arm/live. */
}

ZTEST(actuators, test_real_faults_override_cleared_self_test)
{
    struct self_test test;
    self_test_reset(&test);
    self_test_input(&test, 0, SELF_TEST_BUTTON);
    self_test_input(&test, 30, 0);
    self_test_input(&test, 100, SELF_TEST_BUTTON);
    zassert_false(test.active);
    struct actuator_policy p = actuator_policy_evaluate(TIMEOUT, false, false, test.active, 32767, 300000);
    struct drive_control motor;
    drive_init(&motor);
    zassert_equal(p.reported_state, TIMEOUT);
    zassert_true(p.hazards);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 100).mode, DRIVE_BRAKE);
    struct servo_control servo = calibrated();
    servo_arm(&servo, 0, false); servo_live(&servo, true, false, 0);
    servo_tick(&servo, 100, p.linked, p.inhibit_servo, 0);
    zassert_equal(servo.mode, SERVO_OFF);
    p = actuator_policy_evaluate(LINK_OK, true, false, false, 32767, 300000);
    zassert_equal(p.reported_state, MOTOR_FAULT);
    zassert_true(p.hazards && p.inhibit_servo);
    p = actuator_policy_evaluate(LINK_OK, false, true, false, 32767, 300000);
    zassert_equal(p.reported_state, ACTUATOR_FAULT);
    zassert_true(p.hazards && p.inhibit_servo);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 101).mode, DRIVE_BRAKE);
}

ZTEST(actuators, test_b1_remains_latched_with_self_test_recovery)
{
    struct drive_control motor;
    drive_init(&motor);
    struct actuator_policy p = actuator_policy_evaluate(LINK_OK, false, false, false, 32767, 300000);
    drive_step(&motor, p.drive, 0, 0, 0);
    p.drive.local_stop = true;
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 10).mode, DRIVE_COAST);
    zassert_equal(motor.fault, DRIVE_B1_STOP);
    p = actuator_policy_evaluate(LINK_OK, true, false, false, 32767, 300000);
    zassert_equal(p.reported_state, MOTOR_FAULT);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 20).mode, DRIVE_COAST);
}

ZTEST(actuators, test_paddle_steering_and_brake_remain_independent)
{
    struct blinker lamps;
    struct drive_control motor;
    struct servo_control servo = calibrated();
    blinker_reset(&lamps); drive_init(&motor);
    blinker_step(&lamps, 0, true, false, 0, 0);
    struct actuator_policy p = actuator_policy_evaluate(LINK_OK, false, false, false, -32768, 300000);
    struct blink_output out = blinker_step(&lamps, 20, p.linked, p.hazards, BLINK_LEFT_BUTTON, 0);
    zassert_true(out.left && !out.right);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 20).mode, DRIVE_BRAKE);
    zassert_false(p.inhibit_servo); /* Pedal brake does not disable steering. */
    zassert_equal(servo_map(&servo, -32768), 1200);
    zassert_equal(servo_map(&servo, 0), 1600);
    zassert_equal(servo_map(&servo, 32767), 2000);
    blinker_step(&lamps, 30, true, false, 0, -9000);
    out = blinker_step(&lamps, 40, true, false, 0, -5000);
    zassert_false(out.left || out.right);
}
ZTEST_SUITE(actuators, NULL, NULL, NULL, NULL, NULL);

ZTEST(actuators, test_three_missed_commands_stop_at_boundary)
{
    struct drive_control motor;
    drive_init(&motor);
    uint32_t last_received = 40; /* Commands at 0, 20 and 40 ms, then silence. */
    zassert_false(lab_link_expired(99, last_received));
    struct actuator_policy p = actuator_policy_evaluate(LINK_OK, false, false, false, 32767, 300000);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 99).mode, DRIVE_FORWARD);
    zassert_true(lab_link_expired(100, last_received));
    p = actuator_policy_evaluate(TIMEOUT, false, false, false, 32767, 300000);
    zassert_equal(drive_step(&motor, p.drive, 0, 0, 100).mode, DRIVE_BRAKE);
    zassert_true(p.hazards);
    zassert_false(lab_link_expired(100, 80)); /* A fresh command resets the deadline. */
}
ZTEST(actuators, test_command_age_wrap)
{
    uint32_t last_received = UINT32_MAX - 29;
    zassert_false(lab_link_expired(29, last_received));
    zassert_true(lab_link_expired(30, last_received));
    zassert_true(lab_link_expired(31, last_received));
}
