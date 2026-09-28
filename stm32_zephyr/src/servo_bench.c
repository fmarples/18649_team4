/* Main owns Pi-driven steering. USB is optional for diagnostics/manual calibration. */
#include <zephyr/kernel.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/atomic.h>
#include <stdio.h>
#include <string.h>
#include "servo_core.h"
#include "servo_calibration.h"
#include "servo_bench.h"
static const struct pwm_dt_spec pwm = PWM_DT_SPEC_GET(DT_NODELABEL(steering_servo));
static const struct device *const console = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));
static struct servo_control servo;
static uint16_t applied;
static char line[80];
static size_t used;
static bool discard;
K_MSGQ_DEFINE(console_rx, sizeof(uint8_t), 256, 1);
static atomic_t console_overflow;
struct servo_control servo_bench_snapshot(void) { return servo; }
struct servo_reply { bool ok; struct servo_control snapshot; };
K_MSGQ_DEFINE(console_tx, sizeof(struct servo_reply), 8, 4);

static void console_rx_callback(const struct device *dev, void *unused)
{
 uint8_t ch; ARG_UNUSED(unused);
 uart_irq_update(dev);
 if (uart_irq_rx_ready(dev) <= 0) return;
 while (uart_fifo_read(dev, &ch, 1) == 1) {
  if (k_msgq_put(&console_rx, &ch, K_NO_WAIT) != 0) atomic_set(&console_overflow, 1);
 }
}

void servo_bench_off(void)
{
 servo.mode = SERVO_OFF; servo.pulse = 0;
 if (pwm_is_ready_dt(&pwm)) (void)pwm_set_dt(&pwm, PWM_USEC(SERVO_PERIOD_US), 0);
 applied = 0;
}

int servo_bench_init(void)
{
 servo_reset(&servo);
 servo.left = SERVO_DEFAULT_LEFT_US;
 servo.center = SERVO_DEFAULT_CENTER_US;
 servo.right = SERVO_DEFAULT_RIGHT_US;
 servo.marks = 7;
 if (!servo_auto(&servo)) return -EINVAL;
 if (!pwm_is_ready_dt(&pwm) || !device_is_ready(console)) return -ENODEV;
 int rc = pwm_set_dt(&pwm, PWM_USEC(SERVO_PERIOD_US), 0);
 if (rc) return rc;
 rc = uart_irq_callback_user_data_set(console, console_rx_callback, NULL);
 if (!rc) uart_irq_rx_enable(console);
 return rc;
}
static void reply(bool ok)
{
 struct servo_reply pending = { .ok = ok, .snapshot = servo };
 (void)k_msgq_put(&console_tx, &pending, K_NO_WAIT);
}
void servo_bench_print_replies(void)
{
 struct servo_reply pending;
 /* Bound diagnostic work even if another producer floods the command queue. */
 for (int i = 0; i < 8 && k_msgq_get(&console_tx, &pending, K_NO_WAIT) == 0; i++) {
  const struct servo_control *s = &pending.snapshot;
  printk("SERVO %s mode=%u pulse=%u left=%u center=%u right=%u marks=%u valid=%u\n",
   pending.ok ? "OK" : "ERR", s->mode, s->pulse, s->left, s->center,
   s->right, s->marks, servo_cal_valid(s));
 }
}
static void command(uint64_t now, bool linked, bool self_test, int32_t steer)
{
 bool ok = false;
 int delta, l, c, r; char extra;
 if (!strcmp(line, "SERVO KEEPALIVE")) { servo.heartbeat_ms = now; return; }
 if (!strcmp(line, "SERVO STATUS")) ok = true;
 else if (!strcmp(line, "SERVO OFF")) { servo.mode = SERVO_OFF; servo.pulse = 0; ok = true; }
 else if (!strcmp(line, "SERVO AUTO")) ok = servo_auto(&servo);
 else if (!strcmp(line, "SERVO ARM")) ok = servo_arm(&servo, now, self_test);
 else if (sscanf(line, "SERVO STEP %d %c", &delta, &extra) == 1) ok = servo_step(&servo, delta);
 else if (!strcmp(line, "SERVO MARK LEFT")) ok = servo_mark(&servo, 1);
 else if (!strcmp(line, "SERVO MARK CENTER")) ok = servo_mark(&servo, 2);
 else if (!strcmp(line, "SERVO MARK RIGHT")) ok = servo_mark(&servo, 4);
 else if (!strcmp(line, "SERVO CENTER") && servo.mode == SERVO_MANUAL && (servo.marks & 2)) {
  servo.pulse = servo.center; ok = true;
 } else if (!strcmp(line, "SERVO LIVE")) ok = servo_live(&servo, linked, self_test, steer);
 else if (sscanf(line, "SERVO LOAD %d %d %d %c", &l, &c, &r, &extra) == 3 && servo.mode == SERVO_OFF &&
          l >= 500 && l <= 2500 && c >= 500 && c <= 2500 && r >= 500 && r <= 2500) {
  struct servo_control candidate = { .left = l, .center = c, .right = r, .marks = 7 };
  if (servo_cal_valid(&candidate)) { servo = candidate; ok = true; }
 }
 reply(ok);
}
int servo_bench_service(bool linked, bool self_test, int32_t steer)
{
 uint64_t now = k_uptime_get();
 if (atomic_set(&console_overflow, 0)) {
  servo_bench_off(); k_msgq_purge(&console_rx); used = 0; discard = true;
 }
 /* Bounded input work: long/noisy console traffic cannot starve the Pi link. */
 unsigned char ch;
 for (int i = 0; i < 24 && k_msgq_get(&console_rx, &ch, K_NO_WAIT) == 0; i++) {
  if (ch == '\r') continue;
  if (ch == '\n') {
   line[used] = 0;
   if (!discard && used) command(now, linked, self_test, steer);
   else if (discard) reply(false);
   used = 0; discard = false;
  } else if (used < sizeof(line) - 1 && !discard) line[used++] = ch;
  else discard = true;
 }
 servo_tick(&servo, now, linked, self_test, steer);
 uint16_t wanted = servo.mode == SERVO_OFF ? 0 : servo.pulse;
 if (wanted != applied) {
  int rc = pwm_set_dt(&pwm, PWM_USEC(SERVO_PERIOD_US), PWM_USEC(wanted));
  if (rc) {
   servo.mode = SERVO_OFF; servo.pulse = 0;
   (void)pwm_set_dt(&pwm, PWM_USEC(SERVO_PERIOD_US), 0);
   /* Main applies motor braking before reporting this peripheral failure. */
   return rc;
  }
  applied = wanted;
 }
 return 0;
}
