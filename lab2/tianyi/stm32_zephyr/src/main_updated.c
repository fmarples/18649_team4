/*
 * Part 3/4 STM32 application.
 * Preserves the team's Part 2 UART command/status protocol.
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/atomic.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "encoder.h"
#include "motor.h"
#include "servo.h"
#include "blinker.h"
#include "current.h"

#define COMMAND_SIZE 28
#define STATUS_SIZE 56
#define LINK_TIMEOUT_MS 80U

enum { WAITING = 0, LINK_OK, TIMEOUT, BAD_INPUT, RX_OVERFLOW };

static const char *const state_names[] = {
	"WAITING", "LINK_OK", "ERROR_TIMEOUT",
	"ERROR_BAD_INPUT", "ERROR_RX_OVERFLOW"
};

static const struct device *const link_uart =
	DEVICE_DT_GET(DT_NODELABEL(usart1));

static const struct gpio_dt_spec led =
	GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);

struct packet {
	uint8_t bytes[COMMAND_SIZE];
	uint32_t received_ms;
};

K_MSGQ_DEFINE(rx_queue, sizeof(struct packet), 8, 4);
K_MUTEX_DEFINE(state_mutex);
K_SEM_DEFINE(status_due, 0, 1);
static atomic_t overflow;

static struct {
	uint32_t state, command_seq, received_ms, rejected;
	int32_t steer, throttle, brake;
	uint32_t buttons;
	bool ever_received;
} state = {
	.state = WAITING,
	.throttle = 32767,
	.brake = -32768
};

#define STEER_INPUT_MAX_DEG 360.0f
#define SERVO_OUTPUT_MAX_DEG 45.0f
#define MAX_WHEEL_VELOCITY_MPS 1.0f

#define BUTTON_LEFT_BIT 0U
#define BUTTON_RIGHT_BIT 1U

static float raw_to_steering_deg(int32_t raw)
{
	return ((float)raw / 32767.0f) * STEER_INPUT_MAX_DEG;
}

static float steering_to_servo_deg(float steering_deg)
{
	float servo = (steering_deg / STEER_INPUT_MAX_DEG) *
		      SERVO_OUTPUT_MAX_DEG;

	if (servo > SERVO_OUTPUT_MAX_DEG) servo = SERVO_OUTPUT_MAX_DEG;
	if (servo < -SERVO_OUTPUT_MAX_DEG) servo = -SERVO_OUTPUT_MAX_DEG;
	return servo;
}

static float raw_to_percent(int32_t raw)
{
	float percent = ((float)(32767 - raw) / 65535.0f) * 100.0f;

	if (percent < 0.0f) percent = 0.0f;
	if (percent > 100.0f) percent = 100.0f;
	return percent;
}

static void apply_safe_outputs(void)
{
	(void)motor_dynamic_brake();
	(void)servo_set_angle_deg(0.0f);
	(void)blinker_set_hazard(true);
}

static void apply_normal_outputs(int32_t steer_raw,
				 int32_t throttle_raw,
				 int32_t brake_raw,
				 uint32_t buttons)
{
	float steering_deg = raw_to_steering_deg(steer_raw);
	float brake_percent = raw_to_percent(brake_raw);
	float throttle_percent = raw_to_percent(throttle_raw);

	/*
	 * Brake priority: throttle is never applied while the brake is active.
	 */
	if (brake_percent > 0.0f) {
		(void)motor_dynamic_brake();
	} else {
		float target =
			(throttle_percent / 100.0f) *
			MAX_WHEEL_VELOCITY_MPS;

		(void)motor_set_velocity(target, target);
	}

	(void)servo_set_angle_deg(
		steering_to_servo_deg(steering_deg));

	(void)blinker_set_hazard(false);

	bool left =
		(buttons & BIT(BUTTON_LEFT_BIT)) != 0U;
	bool right =
		(buttons & BIT(BUTTON_RIGHT_BIT)) != 0U;

	(void)blinker_update(left, right, steering_deg);
}

static bool header_ok(const uint8_t *b)
{
	return b[0] == 'L' && b[1] == '2' &&
	       b[2] == 1 && b[3] == 1;
}

/* ISR only collects fixed-size candidates. Validation runs outside ISR. */
static void rx_callback(const struct device *dev, void *unused)
{
	static struct packet candidate;
	static size_t used;
	uint8_t byte;

	ARG_UNUSED(unused);
	uart_irq_update(dev);

	if (uart_irq_rx_ready(dev) <= 0)
		return;

	while (uart_fifo_read(dev, &byte, 1) == 1) {
		candidate.bytes[used++] = byte;

		if (used >= 4 && !header_ok(candidate.bytes))
			memmove(candidate.bytes, candidate.bytes + 1, --used);

		if (used == COMMAND_SIZE) {
			candidate.received_ms = k_uptime_get_32();

			if (k_msgq_put(&rx_queue, &candidate, K_NO_WAIT) != 0) {
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
	state.throttle = 32767;
	state.brake = -32768;
	state.buttons = 0;

	/*
	 * Do not rely on the safe internal values alone: drive the hardware
	 * outputs into the fail-safe state.
	 */
	apply_safe_outputs();
}

static void accept_candidate(const struct packet *p)
{
	const uint8_t *b = p->bytes;

	int32_t steer = (int32_t)sys_get_le32(b + 8);
	int32_t throttle = (int32_t)sys_get_le32(b + 12);
	int32_t brake = (int32_t)sys_get_le32(b + 16);
	uint32_t buttons = sys_get_le32(b + 20);
	uint32_t seq = sys_get_le32(b + 4);

	bool fresh =
		k_uptime_get_32() - p->received_ms < LINK_TIMEOUT_MS;

	bool valid =
		crc32_ieee(b, 24) == sys_get_le32(b + 24) &&
		steer >= -32768 && steer <= 32767 &&
		throttle >= -32768 && throttle <= 32767 &&
		brake >= -32768 && brake <= 32767 &&
		(buttons & ~0x7ffU) == 0;

	k_mutex_lock(&state_mutex, K_FOREVER);

	if (!fresh) {
		state.rejected++;
		set_error(TIMEOUT);
	} else if (!valid) {
		state.rejected++;
		set_error(BAD_INPUT);
	} else if (!state.ever_received ||
		   state.state != LINK_OK ||
		   (seq - state.command_seq > 0U &&
		    seq - state.command_seq < 0x80000000U)) {

		state.steer = steer;
		state.throttle = throttle;
		state.brake = brake;
		state.buttons = buttons;
		state.command_seq = seq;
		state.received_ms = p->received_ms;
		state.ever_received = true;
		state.state = LINK_OK;

		apply_normal_outputs(
			steer, throttle, brake, buttons);
	}

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

	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);

	while (true) {
		int32_t left_mA = INT32_MIN;
		int32_t right_mA = INT32_MIN;
		int32_t servo_mA = INT32_MIN;
		uint32_t current_valid = 0;

		k_sem_take(&status_due, K_FOREVER);

		(void)current_get_mA(
			&left_mA, &right_mA,
			&servo_mA, &current_valid);

		memset(frame, 0, sizeof(frame));

		frame[0] = 'L';
		frame[1] = '2';
		frame[2] = 1;
		frame[3] = 2;

		sys_put_le32(seq++, frame + 4);
		sys_put_le32(k_uptime_get_32(), frame + 8);

		k_mutex_lock(&state_mutex, K_FOREVER);
		sys_put_le32(state.command_seq, frame + 12);
		sys_put_le32(state.state, frame + 16);
		sys_put_le32((uint32_t)state.steer, frame + 20);
		sys_put_le32((uint32_t)state.throttle, frame + 24);
		sys_put_le32((uint32_t)state.brake, frame + 28);
		sys_put_le32(state.rejected, frame + 48);
		k_mutex_unlock(&state_mutex);

		sys_put_le32((uint32_t)left_mA, frame + 32);
		sys_put_le32((uint32_t)right_mA, frame + 36);
		sys_put_le32((uint32_t)servo_mA, frame + 40);
		sys_put_le32(current_valid, frame + 44);

		sys_put_le32(crc32_ieee(frame, 52), frame + 52);

		for (size_t i = 0; i < sizeof(frame); ++i)
			uart_poll_out(link_uart, frame[i]);
	}
}

K_THREAD_DEFINE(status_tid, 1536, status_thread,
		NULL, NULL, NULL, 2, 0, 0);

static void console_thread(void *a, void *b, void *c)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);

	while (true) {
		k_mutex_lock(&state_mutex, K_FOREVER);

		uint32_t mode = state.state;
		uint32_t seq = state.command_seq;
		uint32_t bad = state.rejected;
		uint32_t age =
			state.ever_received ?
			k_uptime_get_32() - state.received_ms : 0;

		int32_t steer = state.steer;
		int32_t throttle = state.throttle;
		int32_t brake = state.brake;

		k_mutex_unlock(&state_mutex);

		printk("STM %s seq=%u steer=%d thr=%d brk=%d age=%ums rejected=%u vel=%.3f\n",
		       state_names[mode], seq, steer, throttle, brake, age, bad,
		       (double)encoder_get_average_velocity_mps());

		k_msleep(250);
	}
}

K_THREAD_DEFINE(console_tid, 1536, console_thread,
		NULL, NULL, NULL, 3, 0, 0);

int main(void)
{
	if (!device_is_ready(link_uart) ||
	    !gpio_is_ready_dt(&led)) {
		printk("ERROR: UART or LED unavailable\n");
		(void)motor_dynamic_brake();
		(void)blinker_set_hazard(true);
		return 1;
	}

	if (gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE) != 0 ||
	    uart_irq_callback_user_data_set(
		    link_uart, rx_callback, NULL) != 0) {
		printk("ERROR: device configuration failed\n");
		(void)motor_dynamic_brake();
		(void)blinker_set_hazard(true);
		return 1;
	}

	/*
	 * Initialize hardware drivers before enabling normal operation.
	 */
	if (motor_init() != 0 ||
	    encoder_init() != 0 ||
	    servo_init() != 0 ||
	    blinker_init() != 0 ||
	    current_init() != 0) {
		printk("ERROR: hardware initialization failed\n");
		(void)motor_dynamic_brake();
		(void)blinker_set_hazard(true);
		return 1;
	}

	k_mutex_lock(&state_mutex, K_FOREVER);
	set_error(WAITING);
	k_mutex_unlock(&state_mutex);

	uart_irq_rx_enable(link_uart);
	k_timer_start(&status_timer, K_MSEC(20), K_MSEC(20));

	printk("PART 3/4: USART1 TX=PA9/D8 RX=PA10/D2, 115200 8N1\n");
	printk("Hardware drivers initialized; startup remains fail-safe.\n");

	while (true) {
		struct packet p;

		if (k_msgq_get(&rx_queue, &p, K_MSEC(1)) == 0)
			accept_candidate(&p);

		k_mutex_lock(&state_mutex, K_FOREVER);

		if (atomic_set(&overflow, 0) != 0) {
			state.rejected++;
			set_error(RX_OVERFLOW);
		}

		if (state.state == LINK_OK &&
		    k_uptime_get_32() - state.received_ms >=
		    LINK_TIMEOUT_MS) {
			set_error(TIMEOUT);
		}

		bool linked = state.state == LINK_OK;
		k_mutex_unlock(&state_mutex);

		if (gpio_pin_set_dt(&led, linked) != 0) {
			printk("ERROR: LED update failed\n");
			(void)motor_dynamic_brake();
			(void)blinker_set_hazard(true);
			return 1;
		}
	}
}
