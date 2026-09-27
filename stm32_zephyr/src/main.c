/* CRC Pi link, encoder/PID motors, blinkers/self-test, opt-in steering bench. */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/atomic.h>
#include <string.h>
#include <stdint.h>
#include "throttle_mapping.h"
#include "motor_driver.h"
#include "actuator_policy.h"
#include "blinker_core.h"
#include "blinker_gpio.h"
#include "self_test.h"
#include "servo_bench.h"

#define COMMAND_SIZE 28
#define STATUS_SIZE 56
#define LINK_TIMEOUT_MS 80U
static const char *const state_names[] = {
	"WAITING", "LINK_OK", "ERROR_TIMEOUT", "ERROR_BAD_INPUT", "ERROR_RX_OVERFLOW",
	"ERROR_MOTOR", "SELF_TEST", "ERROR_ACTUATOR"
};
BUILD_ASSERT(CONFIG_MAIN_THREAD_PRIORITY < 2,
             "Link/motor owner must outrank status and console threads");
static const struct device *const link_uart = DEVICE_DT_GET(DT_NODELABEL(usart1));
/* PA5/D13 (including onboard LD2) belongs only to the front-right blinker. */
static struct blinker blink;
static struct self_test self_test;
struct packet { uint8_t bytes[COMMAND_SIZE]; uint32_t received_ms; };
K_MSGQ_DEFINE(rx_queue, sizeof(struct packet), 8, 4);
K_MUTEX_DEFINE(state_mutex);
K_SEM_DEFINE(status_due, 0, 1);
static atomic_t overflow;
static struct {
	uint32_t state, command_seq, received_ms, rejected;
	int32_t steer, throttle, brake;
	uint32_t buttons, target_mrpm;
	struct motor_report motor;
	bool ever_received;
	bool actuator_fault;
	enum blink_mode blink_mode;
	bool blink_left, blink_right;
} state = { .state = WAITING, .throttle = 32767, .brake = -32768 };

/* Caller holds state_mutex; all actuator decisions share this policy. */
static struct actuator_policy current_policy(void)
{
	return actuator_policy_evaluate(state.state, state.motor.fault != 0,
		state.actuator_fault, self_test.active, state.brake, state.target_mrpm);
}

static bool header_ok(const uint8_t *b)
{
	return b[0] == 'L' && b[1] == '2' && b[2] == 1 && b[3] == 1;
}

/* ISR only collects fixed-size candidates. CRC/range checks run in main. */
static void rx_callback(const struct device *dev, void *unused)
{
	static struct packet candidate;
	static size_t used;
	uint8_t byte;
	ARG_UNUSED(unused);
	uart_irq_update(dev);
	if (uart_irq_rx_ready(dev) <= 0) {
		return;
	}
	while (uart_fifo_read(dev, &byte, 1) == 1) {
		candidate.bytes[used++] = byte;
		if (used >= 4 && !header_ok(candidate.bytes)) {
			memmove(candidate.bytes, candidate.bytes + 1, --used);
		}
		if (used == COMMAND_SIZE) {
			candidate.received_ms = k_uptime_get_32();
			if (k_msgq_put(&rx_queue, &candidate, K_NO_WAIT) != 0) {
				/* Drop the backlog, never apply queued stale throttle later. */
				k_msgq_purge(&rx_queue);
				atomic_set(&overflow, 1);
			}
			used = 0;
		}
	}
}

static void set_error(uint32_t reason)
{
	state.state = reason;
	state.steer = 0;
	state.throttle = 32767; /* Released pedal in this Windows mapping. */
	state.brake = -32768;  /* Link/input errors request dynamic braking. */
	state.buttons = 0;
	state.target_mrpm = 0;
}

static void accept_candidate(const struct packet *p)
{
	const uint8_t *b = p->bytes;
	int32_t steer = (int32_t)sys_get_le32(b + 8);
	int32_t throttle = (int32_t)sys_get_le32(b + 12);
	int32_t brake = (int32_t)sys_get_le32(b + 16);
	uint32_t buttons = sys_get_le32(b + 20);
	uint32_t seq = sys_get_le32(b + 4);
	bool fresh = k_uptime_get_32() - p->received_ms < LINK_TIMEOUT_MS;
	bool valid = crc32_ieee(b, 24) == sys_get_le32(b + 24) &&
		steer >= -32768 && steer <= 32767 &&
		throttle >= -32768 && throttle <= 32767 &&
		brake >= -32768 && brake <= 32767 && (buttons & ~0x7ffU) == 0;

	k_mutex_lock(&state_mutex, K_FOREVER);
	if (!fresh) {
		state.rejected++;
		set_error(TIMEOUT);
	} else if (!valid) {
		state.rejected++;
		set_error(BAD_INPUT);
	} else if (!state.ever_received || state.state != LINK_OK ||
		   (seq - state.command_seq > 0U && seq - state.command_seq < 0x80000000U)) {
		state.steer = steer;
		state.throttle = throttle;
		state.brake = brake;
		state.buttons = buttons;
		/* Any brake input overrides throttle, including its startup request. */
		state.target_mrpm = pedal_target_mrpm(throttle, brake);
		state.command_seq = seq;
		state.received_ms = p->received_ms;
		state.ever_received = true;
		state.state = LINK_OK;
		self_test_input(&self_test, k_uptime_get(), buttons);
	}
	/* Duplicate/old sequences while linked do not refresh the timeout. */
	k_mutex_unlock(&state_mutex);
}

static void status_tick(struct k_timer *timer)
{
	ARG_UNUSED(timer);
	k_sem_give(&status_due);
}
K_TIMER_DEFINE(status_timer, status_tick, NULL);

static void status_thread(void *a, void *b, void *c)
{
	uint32_t seq = 0;
	uint8_t frame[STATUS_SIZE];
	ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
	while (true) {
		k_sem_take(&status_due, K_FOREVER);
		memset(frame, 0, sizeof(frame));
		frame[0] = 'L'; frame[1] = '2'; frame[2] = 1; frame[3] = 2;
		sys_put_le32(seq++, frame + 4);
		sys_put_le32(k_uptime_get_32(), frame + 8);
		k_mutex_lock(&state_mutex, K_FOREVER);
		sys_put_le32(state.command_seq, frame + 12);
		sys_put_le32(current_policy().reported_state, frame + 16);
		sys_put_le32((uint32_t)state.steer, frame + 20);
		sys_put_le32((uint32_t)state.throttle, frame + 24);
		sys_put_le32((uint32_t)state.brake, frame + 28);
		sys_put_le32(state.rejected, frame + 48);
		k_mutex_unlock(&state_mutex);
		/* INT32_MIN means unavailable, never a fabricated zero-current reading. */
		sys_put_le32(0x80000000U, frame + 32);
		sys_put_le32(0x80000000U, frame + 36);
		sys_put_le32(0x80000000U, frame + 40);
		sys_put_le32(0, frame + 44); /* Current-valid mask: none wired. */
		sys_put_le32(crc32_ieee(frame, 52), frame + 52);
		for (size_t i = 0; i < sizeof(frame); ++i) {
			uart_poll_out(link_uart, frame[i]);
		}
	}
}
K_THREAD_DEFINE(status_tid, 1536, status_thread, NULL, NULL, NULL, 2, 0, 0);

static void console_thread(void *a, void *b, void *c)
{
	ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
	int64_t next_diagnostic_ms = 0;
	while (true) {
		servo_bench_print_replies();
		if (k_uptime_get() < next_diagnostic_ms) {
			k_msleep(10);
			continue;
		}
		next_diagnostic_ms = k_uptime_get() + 250;
		k_mutex_lock(&state_mutex, K_FOREVER);
		uint32_t mode = current_policy().reported_state, seq = state.command_seq, bad = state.rejected;
		uint32_t age = state.ever_received ? k_uptime_get_32() - state.received_ms : 0;
		int32_t steer = state.steer, throttle = state.throttle, brake = state.brake;
		uint32_t target = state.target_mrpm;
		struct motor_report motor = state.motor;
		enum blink_mode blink_mode = state.blink_mode;
		bool left = state.blink_left, right = state.blink_right;
		k_mutex_unlock(&state_mutex);
		printk("STM %s seq=%u steer=%d thr=%d brk=%d target_mrpm=%u age=%ums rejected=%u blink=%s L=%u R=%u\n",
		       state_names[mode], seq, steer, throttle, brake, target, age, bad,
		       blinker_mode_name(blink_mode), left, right);
		printk("DRIVE mode=%u target_mrpm=%u left_mrpm=%d right_mrpm=%d avg_mrpm=%d "
		       "duty_mpercent=%u left_count=%d right_count=%d t_ms=%lld fault=%d\n",
		       (unsigned)motor.mode, motor.target_mrpm, motor.left_mrpm, motor.right_mrpm,
		       motor.average_mrpm, motor.duty_mpercent, motor.left_count, motor.right_count,
		       (long long)motor.sample_ms, motor.fault);
		k_msleep(10);
	}
}
K_THREAD_DEFINE(console_tid, 1536, console_thread, NULL, NULL, NULL, 3, 0, 0);

/* Returning from main must never leave enabled bridges without a B1 owner. */
static void stop_on_init_failure(void)
{
	struct motor_report report = motor_update((struct drive_input){.sensor_fault = true});
	k_mutex_lock(&state_mutex, K_FOREVER);
	state.motor = report;
	set_error(MOTOR_FAULT);
	k_mutex_unlock(&state_mutex);
}

int main(void)
{
	/* Initialize outputs first. Until the first valid command, request braking. */
	int motor_error = motor_init();
	struct motor_report initial = motor_update((struct drive_input){0});
	k_mutex_lock(&state_mutex, K_FOREVER);
	state.motor = initial;
	if (motor_error || initial.fault) { set_error(MOTOR_FAULT); }
	k_mutex_unlock(&state_mutex);
	if (!device_is_ready(link_uart)) {
		stop_on_init_failure();
		printk("ERROR: UART unavailable\n");
		return 1;
	}
	if (blinker_gpio_init() != 0 || servo_bench_init() != 0 ||
	    uart_irq_callback_user_data_set(link_uart, rx_callback, NULL) != 0) {
		stop_on_init_failure();
		servo_bench_off();
		printk("ERROR: device configuration failed\n");
		return 1;
	}
	blinker_reset(&blink);
	self_test_reset(&self_test);
	uart_irq_rx_enable(link_uart);
	k_timer_start(&status_timer, K_MSEC(20), K_MSEC(20));
	printk("PI MOTOR CONTROL: USART1 TX=PA9/D8 RX=PA10/D2, 115200 8N1\n");
	printk("1320 counts/rev; cutoff=23 RPM; full pedal=300 RPM; start=60%%/200ms; PID=40..100%%.\n");
	printk("Brake/link error=dynamic brake; released pedal=coast; B1=latch off until reset.\n");
	printk("DRIVE modes: 0=coast 1=forward 2=brake; faults: 1=B1 2=sensor/GPIO 3=PID data negative=HAL.\n");
	printk("BLINKERS: FL=D10 RL=A2 FR=D13 RR=D15; paddles left=5 right=4.\n");
	printk("SERVO: D14/PB9 50Hz; boot OFF; USB load/arm/live and heartbeat required.\n");
	printk("A single press: self-test hazards + dynamic brake + servo off; double within 400ms clears latch.\n");
	while (true) {
		struct packet p;
		if (k_msgq_get(&rx_queue, &p, K_MSEC(1)) == 0) {
			accept_candidate(&p);
		}
		k_mutex_lock(&state_mutex, K_FOREVER);
		if (atomic_set(&overflow, 0) != 0) {
			state.rejected++;
			set_error(RX_OVERFLOW);
		}
		if (state.state == LINK_OK &&
		    k_uptime_get_32() - state.received_ms >= LINK_TIMEOUT_MS) {
			set_error(TIMEOUT);
		}
		struct actuator_policy policy = current_policy();
		k_mutex_unlock(&state_mutex);
		/* This priority-1 thread owns validation, timeout and all motor writes.
		 * Apply motor stop decisions before processing potentially slow USB replies. */
		struct motor_report report = motor_update(policy.drive);
		k_mutex_lock(&state_mutex, K_FOREVER);
		state.motor = report;
		policy = current_policy(); /* Propagate a newly sampled B1/motor fault now. */
		int32_t steer = state.steer;
		uint32_t buttons = state.buttons;
		bool actuator_fault = state.actuator_fault;
		k_mutex_unlock(&state_mutex);
		int servo_error = 0;
		if (!actuator_fault) {
			servo_error = servo_bench_service(policy.linked, policy.inhibit_servo, steer);
		}
		struct blink_output output = blinker_step(&blink, k_uptime_get(),
			policy.linked, policy.hazards || servo_error != 0, buttons, steer);
		int lamp_error = blinker_gpio_write(output);
		if (servo_error || lamp_error) {
			/* Latch peripheral failures. A healthy H-bridge dynamically brakes;
			 * its own B1/HAL fault still retains the existing enable-low policy. */
			servo_bench_off();
			k_mutex_lock(&state_mutex, K_FOREVER);
			state.actuator_fault = true;
			policy = current_policy();
			k_mutex_unlock(&state_mutex);
			report = motor_update(policy.drive);
			if (!actuator_fault) {
				printk("ERROR: actuator fault servo=%d lamps=%d; reset required\n",
				       servo_error, lamp_error);
			}
		}
		k_mutex_lock(&state_mutex, K_FOREVER);
		state.motor = report;
		state.blink_mode = blink.mode;
		state.blink_left = output.left;
		state.blink_right = output.right;
		k_mutex_unlock(&state_mutex);
	}
}
