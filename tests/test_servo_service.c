/* Production init/service/console paths, replacing only Zephyr hardware boundaries. */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include "servo_bench.h"
uint64_t fake_now;
uint32_t fake_pulse_ns;
int fake_pwm_error;
const struct device fake_console = {0};
const char *fake_input;
void (*fake_rx_callback)(const struct device *, void *);
static char last_reply[256];
int printk(const char *format, ...)
{
 va_list args; va_start(args, format);
 int rc = vsnprintf(last_reply, sizeof(last_reply), format, args);
 va_end(args); return rc;
}

/* Feed an optional console command through the actual interrupt/queue parser. */
static void console_command(const char *input)
{
 fake_input = input;
 fake_rx_callback(&fake_console, NULL);
 for (int i = 0; i < 8; i++) assert(servo_bench_service(true, false, 0) == 0);
 servo_bench_print_replies();
}

int main(void)
{
 assert(servo_bench_init() == 0);
 assert(fake_pulse_ns == 0);
 fake_now = 10000; /* No USB input or KEEPALIVE has ever arrived. */
 assert(servo_bench_service(false, false, 0) == 0);
 assert(fake_pulse_ns == 0);
 assert(servo_bench_service(true, false, 32767) == 0);
 assert(fake_pulse_ns == 0);
 assert(servo_bench_service(true, false, 0) == 0);
 assert(fake_pulse_ns == 1600000);
 fake_now = 20000;
 assert(servo_bench_service(true, false, -32768) == 0);
 assert(fake_pulse_ns == 1200000);
 assert(servo_bench_service(true, false, 32767) == 0);
 assert(fake_pulse_ns == 2000000);
 assert(servo_bench_service(false, false, 32767) == 0);
 assert(fake_pulse_ns == 0);
 assert(servo_bench_service(true, false, 32767) == 0);
 assert(fake_pulse_ns == 0);
 assert(servo_bench_service(true, false, 0) == 0);
 assert(fake_pulse_ns == 1600000);
 assert(servo_bench_service(true, true, 0) == 0);
 assert(fake_pulse_ns == 0);
 assert(servo_bench_service(true, false, 0) == 0);
 assert(fake_pulse_ns == 1600000);
 console_command("SERVO OFF\n");
 assert(fake_pulse_ns == 0);
 fake_now = 30000;
 assert(servo_bench_service(true, false, 0) == 0);
 assert(fake_pulse_ns == 0);
 console_command("SERVO AUTO\n");
 assert(fake_pulse_ns == 1600000);
 console_command("SERVO STATUS\n");
 assert(strstr(last_reply, "mode=2 pulse=1600 left=1200 center=1600 right=2000 marks=7 valid=1"));
 console_command("SERVO OFF\n");
 console_command("SERVO ARM\n");
 assert(fake_pulse_ns == 1600000);
 fake_now += 500;
 assert(servo_bench_service(true, false, 0) == 0);
 assert(fake_pulse_ns == 0);
 console_command("SERVO AUTO\n");
 fake_pwm_error = -5;
 assert(servo_bench_service(true, false, 32767) == -5);
 fake_pwm_error = 0;
 servo_bench_off(); /* Main latches actuator fault and calls this on an output error. */
 assert(fake_pulse_ns == 0);
 assert(servo_bench_service(true, false, 0) == 0);
 assert(fake_pulse_ns == 0);
 puts("PASS: production servo service, no USB, explicit OFF, recovery, manual lease, PWM fault");
 return 0;
}
