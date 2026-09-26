#include <errno.h>
#include <string.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/printk.h>
#include "bench_control.h"
#include "bench_encoders.h"

#define CONTROL_PRIORITY 2
BUILD_ASSERT(CONFIG_MAIN_THREAD_PRIORITY > CONTROL_PRIORITY,
             "Console must run below the motor cutoff thread priority");

static const struct pwm_dt_spec pwms[] = {
    PWM_DT_SPEC_GET(DT_NODELABEL(left_pwm)),
    PWM_DT_SPEC_GET(DT_NODELABEL(right_pwm)),
};
static const struct gpio_dt_spec directions[] = {
    GPIO_DT_SPEC_GET(DT_NODELABEL(in1), gpios),
    GPIO_DT_SPEC_GET(DT_NODELABEL(in2), gpios),
    GPIO_DT_SPEC_GET(DT_NODELABEL(in3), gpios),
    GPIO_DT_SPEC_GET(DT_NODELABEL(in4), gpios),
};
static const struct gpio_dt_spec enables[] = {
    GPIO_DT_SPEC_GET(DT_NODELABEL(ena), gpios),
    GPIO_DT_SPEC_GET(DT_NODELABEL(enb), gpios),
};
/* NUCLEO-F401RE B1 is sw0 / PC13, active low in the board devicetree. */
static const struct gpio_dt_spec user_button = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);
static struct gpio_callback button_callback;
static atomic_t button_latched;
static int button_level;
static const struct device *const console = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

struct command { char text[16]; int64_t received_ms; };
K_MSGQ_DEFINE(commands, sizeof(struct command), 4, 8);
K_MSGQ_DEFINE(rx_bytes, sizeof(unsigned char), 128, 1);
static atomic_t rx_failed;
static atomic_t stop_requested;
static atomic_t hardware_fault;
static atomic_t accepted;
static atomic_t rejected;
static struct k_spinlock snapshot_lock;
enum sample_stage { SAMPLE_OFF, SAMPLE_PULSE, SAMPLE_KICK, SAMPLE_HOLD, SAMPLE_PID };
static const char *const phase_names[] = {"IDLE", "ARMED", "LEFT", "RIGHT", "BOTH"};
static struct {
    enum bench_phase phase;
    enum sample_stage stage;
    struct bench_output output;
    struct bench_encoder_sample encoder;
    int fault;
    unsigned target_rpm;
    struct velocity_control velocity;
} reported;

/* F401 USART has no deep RX FIFO: sleeping/polling loses a burst at 115200.
 * Capture every byte in the ISR; parse and print only from the main thread. */
static void console_rx(const struct device *dev, void *user_data)
{
    ARG_UNUSED(user_data);
    while (uart_irq_update(dev) && uart_irq_rx_ready(dev)) {
        unsigned char byte;
        int count = uart_fifo_read(dev, &byte, 1);
        if (count <= 0) {
            if (count < 0) {
                atomic_set(&rx_failed, 1);
                atomic_set(&stop_requested, 1);
            }
            break;
        }
        if (!atomic_get(&rx_failed) &&
            k_msgq_put(&rx_bytes, &byte, K_NO_WAIT) != 0) {
            atomic_set(&rx_failed, 1);
            atomic_set(&stop_requested, 1);
        }
    }
    if (uart_err_check(dev)) {
        atomic_set(&rx_failed, 1);
        atomic_set(&stop_requested, 1);
    }
}

/* Capture even a short B1 press. The priority-2 thread also polls its level. */
static void button_pressed(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    ARG_UNUSED(dev); ARG_UNUSED(cb); ARG_UNUSED(pins);
    atomic_set(&button_latched, 1);
}

/* Arm B1 before starting the motor thread; failure leaves the enables low. */
static int button_init(void)
{
    if (!gpio_is_ready_dt(&user_button)) { return -ENODEV; }
    int ret = gpio_pin_configure_dt(&user_button, GPIO_INPUT | GPIO_PULL_UP);
    if (ret < 0) { return ret; }
    gpio_init_callback(&button_callback, button_pressed, BIT(user_button.pin));
    ret = gpio_add_callback(user_button.port, &button_callback);
    if (ret < 0) { return ret; }
    return gpio_pin_interrupt_configure_dt(&user_button, GPIO_INT_EDGE_TO_ACTIVE);
}

/* On a HAL failure latch the test off. Reclaim enable pins as GPIO-low too;
 * never resume PWM after this until reboot. Returns an error if this also fails. */
static int force_off(void)
{
    int first_error = 0;
    for (size_t i = 0; i < ARRAY_SIZE(enables); ++i) {
        int ret = gpio_pin_configure_dt(&enables[i], GPIO_OUTPUT_INACTIVE);
        if (ret < 0 && first_error == 0) { first_error = ret; }
    }
    for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
        int ret = gpio_pin_configure_dt(&directions[i], GPIO_OUTPUT_INACTIVE);
        if (ret < 0 && first_error == 0) { first_error = ret; }
    }
    return first_error;
}

static int outputs_init(void)
{
    for (size_t i = 0; i < ARRAY_SIZE(enables); ++i) {
        if (!gpio_is_ready_dt(&enables[i]) || !pwm_is_ready_dt(&pwms[i])) {
            return -ENODEV;
        }
    }
    /* PWM pinctrl has already selected the timer alternate functions. */
    int first_error = 0;
    for (size_t i = 0; i < ARRAY_SIZE(pwms); ++i) {
        int ret = pwm_set_dt(&pwms[i], pwms[i].period, 0);
        if (ret < 0 && first_error == 0) { first_error = ret; }
    }
    for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
        if (!gpio_is_ready_dt(&directions[i])) { return -ENODEV; }
        int ret = gpio_pin_configure_dt(&directions[i], GPIO_OUTPUT_INACTIVE);
        if (ret < 0 && first_error == 0) { first_error = ret; }
    }
    return first_error;
}

static int apply_output(struct bench_output output)
{
    /* Disable both channels before changing any direction state. */
    int first_error = 0;
    for (size_t i = 0; i < ARRAY_SIZE(pwms); ++i) {
        int ret = pwm_set_dt(&pwms[i], pwms[i].period, 0);
        if (ret < 0 && first_error == 0) { first_error = ret; }
    }
    if (first_error) { return first_error; }
    /* Settle for one 10 kHz period before direction changes. */
    k_busy_wait(100);
    /* Forward polarities: reverse LEFT relative to the original raw test. */
    int values[] = {0, output.left_percent ? 1 : 0,
                    output.right_percent ? 1 : 0, 0};
    for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
        int ret = gpio_pin_set_dt(&directions[i], values[i]);
        if (ret < 0) { return ret; }
    }
    float duties[] = {output.left_percent, output.right_percent};
    for (size_t i = 0; i < ARRAY_SIZE(pwms); ++i) {
        if (duties[i]) {
            int ret = pwm_set_dt(&pwms[i], pwms[i].period,
                                 (uint32_t)((float)pwms[i].period * duties[i] / 100.0f));
            if (ret < 0) { return ret; }
        }
    }
    return 0;
}

static void control_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    struct bench_control control;
    struct bench_output applied = {0, 0};
    bench_init(&control);

    for (;;) {
        int pressed = gpio_pin_get_dt(&user_button);
        if (pressed < 0) { atomic_cas(&hardware_fault, 0, pressed); }
        if (pressed > 0) { atomic_set(&button_latched, 1); }
        bench_button_update(&control, atomic_get(&button_latched) != 0);
        if (atomic_get(&button_latched)) { k_msgq_purge(&commands); }
        if (atomic_set(&stop_requested, 0)) {
            (void)bench_command(&control, "STOP", k_uptime_get());
            k_msgq_purge(&commands);
        }
        struct command cmd;
        /* Keep observing coast-down even when a motion fault is latched. */
        struct bench_encoder_sample sample;
        int read_ret = bench_encoders_read(&sample);
        int64_t now = k_uptime_get();
        if (read_ret < 0 || sample.invalid[0] || sample.invalid[1]) {
            atomic_cas(&hardware_fault, 0, read_ret < 0 ? read_ret : -EILSEQ);
        } else if (!atomic_get(&hardware_fault)) {
            bench_encoder_update(&control, sample.counts[0], sample.counts[1], sample.time_ms);
        }
        if (k_msgq_get(&commands, &cmd, K_NO_WAIT) == 0) {
            if (atomic_get(&hardware_fault) || now - cmd.received_ms > 250 ||
                !bench_command(&control, cmd.text, now)) {
                (void)bench_command(&control, "STOP", now);
                atomic_inc(&rejected);
            } else {
                atomic_inc(&accepted);
            }
        }
        int64_t tick_ms = k_uptime_get();
        /* Recheck the IRQ latch after command handling; queued commands cannot
         * re-enable an output after a button event. */
        bench_button_update(&control, atomic_get(&button_latched) != 0);
        struct bench_output output = bench_tick(&control, tick_ms);
        if (control.fault != BENCH_OK) {
            atomic_cas(&hardware_fault, 0, control.fault);
        }
        if (atomic_get(&hardware_fault)) {
            (void)bench_command(&control, "STOP", k_uptime_get());
            output = (struct bench_output){0, 0};
        }
        if (output.left_percent != applied.left_percent ||
            output.right_percent != applied.right_percent) {
            int ret = apply_output(output);
            if (ret < 0) {
                int off_ret = force_off();
                atomic_set(&hardware_fault, off_ret < 0 ? off_ret : ret);
                (void)bench_command(&control, "STOP", k_uptime_get());
                output = (struct bench_output){0, 0};
            }
            applied = output;
        }
        k_spinlock_key_t key = k_spin_lock(&snapshot_lock);
        reported.phase = control.phase;
        reported.output = applied;
        reported.encoder = sample;
        reported.fault = atomic_get(&hardware_fault);
        reported.stage = (control.phase == BENCH_IDLE || control.phase == BENCH_ARMED) ? SAMPLE_OFF :
            !(control.hold_test || control.pid_test) ? SAMPLE_PULSE :
            tick_ms < control.hold_at_ms ? SAMPLE_KICK : control.pid_test ? SAMPLE_PID : SAMPLE_HOLD;
        reported.target_rpm = control.target_rpm;
        reported.velocity = control.velocity;
        button_level = pressed;
        k_spin_unlock(&snapshot_lock, key);
        /* This high-priority thread never logs or waits on console input. */
        k_msleep(1);
    }
}
K_THREAD_DEFINE(control_tid, 2304, control_thread, NULL, NULL, NULL,
                CONTROL_PRIORITY, K_FP_REGS, SYS_FOREVER_MS);

static void status_print(void)
{
    k_spinlock_key_t key = k_spin_lock(&snapshot_lock);
    struct bench_output output = reported.output;
    enum bench_phase phase = reported.phase;
    int b1 = button_level;
    k_spin_unlock(&snapshot_lock, key);
    int pins[6];
    for (size_t i = 0; i < ARRAY_SIZE(directions); ++i) {
        pins[i] = gpio_pin_get_dt(&directions[i]);
    }
    pins[4] = gpio_pin_get_dt(&enables[0]);
    pins[5] = gpio_pin_get_dt(&enables[1]);
    for (size_t i = 0; i < ARRAY_SIZE(pins); ++i) {
        if (pins[i] < 0) {
            atomic_set(&hardware_fault, pins[i]);
            atomic_set(&stop_requested, 1);
        }
    }
    printk("MOTOR phase=%s left=%u right=%u in=%d%d%d%d en=%d%d "
           "fault=%ld accepted=%ld rejected=%ld\n", phase_names[phase],
           (unsigned)(output.left_percent + 0.5f), (unsigned)(output.right_percent + 0.5f),
           pins[0], pins[1], pins[2], pins[3], pins[4], pins[5],
           (long)atomic_get(&hardware_fault), (long)atomic_get(&accepted),
           (long)atomic_get(&rejected));
    printk("BUTTON b1=%d latched=%ld\n", b1, (long)atomic_get(&button_latched));
}

static void encoder_print(void)
{
    struct bench_encoder_sample sample;
    int ret = bench_encoders_read(&sample);
    if (ret < 0) {
        atomic_set(&hardware_fault, ret);
        atomic_set(&stop_requested, 1);
    }
    printk("ENC left=%ld right=%ld left_ab=%d%d right_ab=%d%d "
           "invalid_left=%u invalid_right=%u errors=%u\n",
           (long)sample.counts[0], (long)sample.counts[1],
           (sample.ab[0] >> 1) & 1, sample.ab[0] & 1,
           (sample.ab[1] >> 1) & 1, sample.ab[1] & 1,
           (unsigned)sample.invalid[0], (unsigned)sample.invalid[1],
           (unsigned)sample.errors);
}

/* A coherent control snapshot supplies MCU time, applied duty and raw counts.
 * No printing or host timestamps enter the high-priority cutoff loop. */
static void sample_print(void)
{
    static const char *const stages[] = {"OFF", "PULSE", "KICK", "HOLD", "PID"};
    k_spinlock_key_t key = k_spin_lock(&snapshot_lock);
    struct bench_encoder_sample encoder = reported.encoder;
    struct bench_output output = reported.output;
    enum bench_phase phase = reported.phase;
    enum sample_stage stage = reported.stage;
    int fault = reported.fault;
    unsigned target_rpm = reported.target_rpm;
    struct velocity_control velocity = reported.velocity;
    k_spin_unlock(&snapshot_lock, key);
    printk("SAMPLE t_ms=%lld stage=%s phase=%s left_pct=%u right_pct=%u "
           "left=%ld right=%ld invalid_left=%u invalid_right=%u errors=%u fault=%d\n",
           (long long)encoder.time_ms, stages[stage], phase_names[phase],
           (unsigned)(output.left_percent + 0.5f), (unsigned)(output.right_percent + 0.5f),
           (long)encoder.counts[0], (long)encoder.counts[1],
           (unsigned)encoder.invalid[0], (unsigned)encoder.invalid[1],
           (unsigned)encoder.errors, fault);
    if (target_rpm) {
        /* Milli-RPM and milli-percentage-points keep printf integer-only. Use
         * the estimator timestamp, not the newer raw SAMPLE timestamp. */
        printk("PID t_ms=%lld target=%u left_mrpm=%d right_mrpm=%d avg_mrpm=%d "
               "left_mduty=%d right_mduty=%d p=%d i=%d d=%d trim=%d\n",
               (long long)velocity.sample_ms, target_rpm,
               (int)(velocity.rpm[0] * 1000), (int)(velocity.rpm[1] * 1000),
               (int)(velocity.average_rpm * 1000),
               (int)(output.left_percent * 1000), (int)(output.right_percent * 1000),
               (int)(velocity.p_term * 1000), (int)(velocity.i_term * 1000),
               (int)(velocity.d_term * 1000), 0 /* Legacy trim field; no balancing controller. */);
    }
}

/* Report the compiled limits at boot and on STATUS before a host arms a test. */
static void profile_print(void)
{
    printk("MOTOR BENCH: idle at boot; 10kHz; one-shot %u%% / %dms.\n",
           BENCH_DUTY_PERCENT, BENCH_PULSE_MS);
    printk("HOLD BENCH: 10kHz; kick=%u%%/%dms hold=%u%%/%dms; LEFT/RIGHT/BOTH.\n",
           BENCH_KICK_PERCENT, BENCH_PULSE_MS, BENCH_HOLD_PERCENT, BENCH_HOLD_MS);
    printk("PID_PROFILE min_duty=%u max_duty=%u run_ms=%u sample_ms=%u cpr=%u "
           "kp_milli=%u ki_milli=%u kd_milli=%u filter_ms=%u stop=B1 motion_guard=0\n",
           (unsigned)VELOCITY_RUN_MIN_DUTY, (unsigned)VELOCITY_MAX_DUTY,
           BENCH_PID_MS, VELOCITY_PERIOD_MS, (unsigned)VELOCITY_COUNTS_PER_REV,
           (unsigned)(VELOCITY_KP * 1000 + 0.5f), (unsigned)(VELOCITY_KI * 1000 + 0.5f),
           (unsigned)(VELOCITY_KD * 1000 + 0.5f),
           (unsigned)(VELOCITY_FILTER_SECONDS * 1000 + 0.5f));
}

int main(void)
{
    int ret = outputs_init();
    if (ret < 0 || !device_is_ready(console)) {
        int off_ret = force_off();
        printk("ERROR motor initialization=%d emergency_gpio_off=%d\n", ret, off_ret);
        return ret < 0 ? ret : -ENODEV;
    }
    ret = button_init();
    if (ret < 0) {
        int off_ret = force_off();
        printk("ERROR B1 initialization=%d emergency_gpio_off=%d\n", ret, off_ret);
        return ret;
    }
    ret = bench_encoders_init();
    if (ret < 0) {
        int off_ret = force_off();
        printk("ERROR encoder initialization=%d emergency_gpio_off=%d\n", ret, off_ret);
        return ret;
    }
    ret = uart_irq_callback_user_data_set(console, console_rx, NULL);
    if (ret < 0) {
        int off_ret = force_off();
        printk("ERROR console RX setup=%d emergency_gpio_off=%d\n", ret, off_ret);
        return ret;
    }
    uart_irq_rx_enable(console);
    k_thread_start(control_tid);
    profile_print();
    printk("STARTUP/HOLD: per-wheel 150ms motion cutoff. PID: no motion cutoff or duration cap.\n");
    printk("SCHED control=%d console=%d (lower number runs first).\n",
           CONTROL_PRIORITY, CONFIG_MAIN_THREAD_PRIORITY);
    printk("Commands: STATUS, STOP, ARM then LEFT/RIGHT/BOTH, HOLDLEFT/HOLDRIGHT/HOLDBOTH or PID <positive integer RPM> within 5s; PID 0 stops.\n");
    printk("Forward bridge polarity: LEFT IN=01; RIGHT IN=10.\n");
    printk("PID runs continuously. B1 stops both and latches off until reset.\n");
    printk("Faults: 1=left-stall 2=right-stall 3=left-reversed 4=right-reversed 5=PID-data 6=B1-stop; negative=HAL/encoder.\n");
    printk("ENCODERS: raw x4 counts; calibrated forward signs left=-1 right=+1.\n");

    char line[16];
    size_t used = 0;
    bool discard = false;
    int64_t line_started = 0;
    int64_t next_report = 0;
    for (;;) {
        int64_t now = k_uptime_get();
        if ((used || discard) && now - line_started >= 1000) {
            used = 0;
            discard = false;
            atomic_set(&stop_requested, 1);
        }
        if (atomic_get(&rx_failed)) {
            k_msgq_purge(&rx_bytes);
            used = 0;
            discard = true;
            line_started = now;
            atomic_inc(&rejected);
            atomic_set(&stop_requested, 1);
            atomic_clear(&rx_failed);
        }
        /* Limit work per pass even if serial traffic is continuous. */
        for (unsigned i = 0; i < 32; ++i) {
            unsigned char ch;
            if (k_msgq_get(&rx_bytes, &ch, K_NO_WAIT) != 0) { break; }
            if (ch == '\r') { continue; }
            if (ch == '\n') {
                if (used && !discard) {
                    line[used] = '\0';
                    if (strcmp(line, "STOP") == 0 || strcmp(line, "PID 0") == 0) {
                        atomic_set(&stop_requested, 1);
                    } else if (strcmp(line, "STATUS") == 0) {
                        profile_print();
                    } else {
                        struct command cmd = {.received_ms = k_uptime_get()};
                        memcpy(cmd.text, line, used + 1);
                        if (k_msgq_put(&commands, &cmd, K_NO_WAIT) != 0) {
                            atomic_inc(&rejected);
                            atomic_set(&stop_requested, 1);
                        }
                    }
                }
                used = 0;
                discard = false;
            } else if (!discard) {
                if (!used) { line_started = k_uptime_get(); }
                if (ch < 32 || ch > 126 || used == sizeof(line) - 1) {
                    discard = true;
                    atomic_inc(&rejected);
                    atomic_set(&stop_requested, 1);
                } else {
                    line[used++] = (char)ch;
                }
            }
        }
        if (now >= next_report) {
            status_print();
            k_spinlock_key_t key = k_spin_lock(&snapshot_lock);
            bool pid_active = reported.target_rpm != 0;
            k_spin_unlock(&snapshot_lock, key);
            /* SAMPLE includes raw encoder diagnostics. Skip the redundant ENC
             * line during PID to leave room on the 115200-baud console. */
            if (!pid_active) { encoder_print(); }
            sample_print();
            /* Observe motion without delaying the priority-2 control thread. */
            next_report = now + 50;
        }
        k_msleep(1);
    }
}
