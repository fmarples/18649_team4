/* Part 2 UART, Part 3.4 blinkers, opt-in Part 3.3 servo bench. No motor driver. */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/atomic.h>
#include <string.h>
#include <stdint.h>
#include "blinker_core.h"
#include "blinker_gpio.h"
#include "self_test.h"
#include "servo_bench.h"

#define COMMAND_SIZE 28
#define STATUS_SIZE 56
#define LINK_TIMEOUT_MS 80U
enum { WAITING = 0, LINK_OK, TIMEOUT, BAD_INPUT, RX_OVERFLOW, SELF_TEST };
static const char *const state_names[] = {
	"WAITING", "LINK_OK", "ERROR_TIMEOUT", "ERROR_BAD_INPUT", "ERROR_RX_OVERFLOW", "SELF_TEST"
};
static const struct device *const link_uart = DEVICE_DT_GET(DT_NODELABEL(usart1));
static struct blinker blink;
/* Same main-thread owner as command acceptance and blinker outputs. */
static struct self_test self_test;
struct packet { uint8_t bytes[COMMAND_SIZE]; uint32_t received_ms; };
K_MSGQ_DEFINE(rx_queue, sizeof(struct packet), 8, 4);
K_MUTEX_DEFINE(state_mutex);
K_SEM_DEFINE(status_due, 0, 1);
static atomic_t overflow;
static struct {
	uint32_t state, command_seq, received_ms, rejected;
	int32_t steer, throttle, brake;
	uint32_t buttons;
	bool ever_received;
	enum blink_mode blink_mode;
	bool blink_left, blink_right;
} state = { .state = WAITING, .throttle = 32767, .brake = -32768 };

/* Caller holds state_mutex. Keep link state separate from the manual latch. */
static uint32_t reported_state(void)
{
	return state.state == LINK_OK && self_test.active ? SELF_TEST : state.state;
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
	state.brake = -32768;  /* Fully pressed pedal; no hardware output yet. */
	state.buttons = 0;
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
		sys_put_le32(reported_state(), frame + 16);
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
	while (true) {
		k_mutex_lock(&state_mutex, K_FOREVER);
		uint32_t mode = reported_state(), seq = state.command_seq, bad = state.rejected;
		uint32_t age = state.ever_received ? k_uptime_get_32() - state.received_ms : 0;
		int32_t steer = state.steer, throttle = state.throttle, brake = state.brake;
		enum blink_mode blink_mode = state.blink_mode;
		bool left = state.blink_left, right = state.blink_right;
		k_mutex_unlock(&state_mutex);
		printk("STM %s seq=%u steer=%d thr=%d brk=%d age=%ums rejected=%u blink=%s L=%u R=%u\n",
		       state_names[mode], seq, steer, throttle, brake, age, bad,
		       blinker_mode_name(blink_mode), left, right);
		k_msleep(250);
	}
}
K_THREAD_DEFINE(console_tid, 1536, console_thread, NULL, NULL, NULL, 3, 0, 0);

int main(void)
{
	if (!device_is_ready(link_uart)) {
		printk("ERROR: UART unavailable\n");
		return 1;
	}
	if (blinker_gpio_init() != 0 || servo_bench_init() != 0 ||
	    uart_irq_callback_user_data_set(link_uart, rx_callback, NULL) != 0) {
		printk("ERROR: device configuration failed\n");
		return 1;
	}
	blinker_reset(&blink);
	self_test_reset(&self_test);
	uart_irq_rx_enable(link_uart);
	k_timer_start(&status_timer, K_MSEC(20), K_MSEC(20));
	printk("PART3.4 BLINKERS: USART1 TX=PA9/D8 RX=PA10/D2, 115200 8N1\n");
	printk("FL=red D10, RL=yellow A2, FR=white D13, RR=blue D15\n");
	printk("Paddles left=5 right=4; turn=8000 return=6000 raw counts; no motors\n");
	printk("PART3.3 SERVO: D14/PB9 TIM4_CH4 50Hz; boot DISABLED; USB calibration console\n");
	printk("A button=SELF_TEST: single press hazards; double within 400ms clears latch\n");
	printk("Startup/link errors also select hazards. Physical motor braking not connected.\n");
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
		bool linked = state.state == LINK_OK;
		bool manual_test = self_test.active;
		int32_t current_steer = state.steer;
		bool fault = self_test_fault(&self_test, linked);
		struct blink_output output = blinker_step(&blink, k_uptime_get(),
			linked, fault, state.buttons, state.steer);
		state.blink_mode = blink.mode;
		state.blink_left = output.left;
		state.blink_right = output.right;
		k_mutex_unlock(&state_mutex);
		if (servo_bench_service(linked, manual_test, current_steer) != 0) return 1;
		if (blinker_gpio_write(output) != 0) {
			servo_bench_off();
			(void)blinker_gpio_write((struct blink_output){0});
			printk("ERROR: blinker GPIO update failed\n");
			return 1;
		}
	}
}
