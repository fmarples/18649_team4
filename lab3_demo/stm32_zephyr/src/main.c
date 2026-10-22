/*
 * Lab 3 Part 5 demo for NUCLEO-F401RE zones N2 (front) and N3 (rear).
 * Build once per zone with prj_n2.conf or prj_n3.conf; see ../README.md.
 * Outputs are LEDs, GPIO test points and one PWM test point (SRV on N2,
 * PWM_OUT on N3). No H-bridge or servo driver is assumed to be connected.
 *
 * Thread priorities (lower number runs first; the MCP2515 driver's RX/INT
 * threads are cooperative and run above all of these):
 *   1 RX dispatch   2 RELAY (N2), BLINK   3 STEER / DRIVE   4 TEST_BTN
 *   5 PID (N3)      6 HB_MON              7 HB_TX           8 FORCE_TX (N2)
 *   10 diagnostics
 */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/can.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/watchdog.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/util.h>
#include <soc.h>
#include "can_protocol.h"
#include "frame_history.h"
#include "zone_state.h"
#include "timing_trace.h"
#include "timing_stats.h"
#include "timing_probe.h"

#if defined(CONFIG_LAB3_ZONE_N2) == defined(CONFIG_LAB3_ZONE_N3)
#error "Choose exactly one zone: prj_n2.conf or prj_n3.conf"
#endif
#if defined(CONFIG_LAB3_ZONE_N2)
#include "steering_measurement.h"
#define MY_ZONE ZONE_N2
#define MY_HB_ID ID_HB_N2
#define APP_NAME "N2 FRONT"
#define TP_LEFT TP_FL
#define TP_RIGHT TP_FR
#define ACTUATOR_PERIOD PWM_MSEC(20)
#else
#include "pid_measurement.h"
#define MY_ZONE ZONE_N3
#define MY_HB_ID ID_HB_N3
#define APP_NAME "N3 REAR"
#define TP_LEFT TP_RL
#define TP_RIGHT TP_RR
#define ACTUATOR_PERIOD PWM_USEC(100) /* 10 kHz, as the Lab 2 motor bench */
#endif

#define DEBOUNCE_MS 2
#define SINGLE_PRESS_MS 50  /* R2.5: presses less than 50 ms apart are one press */
#define DOUBLE_PRESS_MS 500 /* student clarification: double press within 500 ms */
#define FAULT_MIN_INTERVAL_MS 20 /* catalog: FAULT minimum interarrival */
#define BLINK_HALF_PERIOD_MS 500
#define RX_QUEUE_DEPTH 32

/* Logical bus 0 = A, 1 = B. Everything below indexes by logical bus. */
#if defined(CONFIG_LAB3_SWAP_CAN_AB)
#define BUS_A_NODE DT_NODELABEL(can_b)
#define BUS_B_NODE DT_NODELABEL(can_a)
#else
#define BUS_A_NODE DT_NODELABEL(can_a)
#define BUS_B_NODE DT_NODELABEL(can_b)
#endif
static const struct device *const can_dev[2] = {DEVICE_DT_GET(BUS_A_NODE), DEVICE_DT_GET(BUS_B_NODE)};
static const struct gpio_dt_spec can_int[2] = {
    GPIO_DT_SPEC_GET(BUS_A_NODE, int_gpios), GPIO_DT_SPEC_GET(BUS_B_NODE, int_gpios),
};
static const struct gpio_dt_spec test_button = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), test_button_gpios);
static const struct pwm_dt_spec actuator_pwm = PWM_DT_SPEC_GET(DT_PATH(zephyr_user));
static const struct device *const watchdog_dev = DEVICE_DT_GET(DT_NODELABEL(iwdg));
static const uint32_t catalog_ids[] = {ID_CTRL, ID_FAULT, ID_HB_N1, ID_HB_N2, ID_HB_N3, ID_BLINK, ID_FORCE};

struct rx_item { struct can_frame frame; uint8_t bus; uint32_t received_ms; };
K_MSGQ_DEFINE(rx_queue, sizeof(struct rx_item), RX_QUEUE_DEPTH, 4);
#if defined(CONFIG_LAB3_RELAY)
K_MSGQ_DEFINE(relay_queue, sizeof(struct rx_item), 16, 4);
#endif
K_SEM_DEFINE(actuator_wake, 0, 1);
K_SEM_DEFINE(blink_wake, 0, 1);
K_SEM_DEFINE(button_wake, 0, 1);
K_EVENT_DEFINE(app_ready);

/* State shared by dispatch, monitor and actuator tasks; guarded by state_lock. */
K_MUTEX_DEFINE(state_lock);
static struct zone_monitor monitor;
static bool zone_error = true;
/* This zone itself failed (own test press or R4.7 isolation), as opposed to
 * the system error state: N2 then holds steering instead of tracking it. */
static bool zone_failed = true;
static struct lab3_ctrl command;
static uint8_t blink_mode, blink_phase;
static bool blink_seen;
static uint32_t blink_ms, blink_count;
static uint8_t tx_seq[ID_FORCE + 1];
static int64_t last_fault_ms;
static bool fault_sent;
/* Own test-button latch: HB_TX stays silent until any FAULT clear (clarification). */
static bool hb_silenced;

/* Dedup and relay claims, guarded by history_lock (dispatch and RELAY). */
K_MUTEX_DEFINE(history_lock);
static struct frame_history history;

static atomic_t rx_dropped, duplicates, bad_crc, tx_rejected[2], tx_completed[2], tx_failed[2];
static atomic_t can_state[2], can_state_changes[2], int_kicks[2];
#if defined(CONFIG_LAB3_RELAY)
static atomic_t relay_sent, relay_failed, relay_stale, relay_dropped;
#endif
static int watchdog_channel = -1;

static void wait_ready(void) { k_event_wait(&app_ready, BIT(0), false, K_FOREVER); }

/* Phase-locked periodic release; overruns skip missed periods instead of drifting. */
static void periodic_wait(int64_t *next_ms, uint32_t period_ms)
{
    *next_ms += period_ms;
    int64_t now = k_uptime_get();
    if (*next_ms <= now) *next_ms += ((now - *next_ms) / period_ms + 1) * period_ms;
    k_sleep(K_TIMEOUT_ABS_MS(*next_ms));
}

/* Recompute the zone state, drive ERR and DEG_A/B, and wake the output tasks
 * on an error-state change. Called by HB_MON every 20 ms and after events that
 * can change the state immediately (CTRL, FAULT, test button, bad input). */
static struct zone_health refresh_state(void)
{
    k_mutex_lock(&state_lock, K_FOREVER);
    struct zone_health h = zone_monitor_evaluate(&monitor, k_uptime_get_32());
    bool failed = hb_silenced || h.isolated;
    bool changed = h.error != zone_error || failed != zone_failed;
    zone_error = h.error;
    zone_failed = failed;
    lab3_trace_set(TP_ERR, h.error);
    lab3_trace_set(TP_DEG_A, h.degraded[0]);
    lab3_trace_set(TP_DEG_B, h.degraded[1]);
    k_mutex_unlock(&state_lock);
    if (changed) {
        k_sem_give(&actuator_wake);
        k_sem_give(&blink_wake);
    }
    return h;
}

static void can_tx_done(const struct device *dev, int status, void *user_data)
{
    ARG_UNUSED(dev);
    unsigned bus = (unsigned)(uintptr_t)user_data;
    atomic_inc(status == 0 ? &tx_completed[bus] : &tx_failed[bus]);
}

/* Queue one frame on one controller; never waits for the wire ACK. */
static int submit(unsigned bus, const struct can_frame *f, k_timeout_t timeout)
{
    if (!lab3_measurement_tx_enabled()) return -EACCES;
    uint32_t start = lab3_timing_start();
    lab3_trace_toggle(bus == 0 ? TP_CAN_TX_A : TP_CAN_TX_B);
    int rc = can_send(can_dev[bus], f, timeout, can_tx_done, (void *)(uintptr_t)bus);
    lab3_timing_end(T_CAN_TX, start);
    return rc;
}

/* The send helper: one sequence number per logical message, queued on A then B
 * back to back. A disconnected bus keeps its three TX buffers full, so the
 * first pass never waits; only then are full mailboxes retried briefly. */
static void send_both(struct can_frame *f)
{
    k_mutex_lock(&state_lock, K_FOREVER);
    f->data[0] = (f->data[0] & 0xF0) | (tx_seq[f->id] & 0x0F);
    tx_seq[f->id]++;
    k_mutex_unlock(&state_lock);
    lab3_seal(f);
    int rc[2];
    for (unsigned bus = 0; bus < 2; ++bus) rc[bus] = submit(bus, f, K_NO_WAIT);
    for (unsigned bus = 0; bus < 2; ++bus) {
        if (rc[bus] == -EAGAIN) rc[bus] = submit(bus, f, K_MSEC(1));
        if (rc[bus] != 0 && rc[bus] != -EACCES) atomic_inc(&tx_rejected[bus]);
    }
}

/* FAULT on both buses, at most one per 20 ms (catalog minimum interval) from
 * this node. Test-button press and clear wait for their slot, so only the
 * TEST_BTN thread may block here; repeatable reports (bad input, zone loss)
 * are dropped inside the interval. */
static void send_fault(uint8_t failing_zone, enum fault_reason reason)
{
    bool must_send = reason == FAULT_TEST_BUTTON || reason == FAULT_CLEAR;
    int64_t now = k_uptime_get();
    k_mutex_lock(&state_lock, K_FOREVER);
    int64_t slot = fault_sent ? MAX(now, last_fault_ms + FAULT_MIN_INTERVAL_MS) : now;
    bool send = must_send || slot == now;
    if (send) { last_fault_ms = slot; fault_sent = true; }
    k_mutex_unlock(&state_lock);
    if (!send) return;
    if (slot > now) k_sleep(K_TIMEOUT_ABS_MS(slot));
    struct can_frame f;
    lab3_pack_fault(&f, failing_zone, reason, MY_ZONE);
    send_both(&f);
}

/* Releasing the latch also resumes heartbeats silenced by this node's test button. */
static void set_latch(bool latched)
{
    k_mutex_lock(&state_lock, K_FOREVER);
    monitor.latched = latched;
    if (!latched) hb_silenced = false;
    k_mutex_unlock(&state_lock);
}

/* Out-of-range or corrupted CTRL: this zone enters error and reports it. */
static void bad_input(enum fault_reason reason)
{
    set_latch(true);
    refresh_state();
    send_fault(MY_ZONE, reason);
}

/* Driver RX callback (MCP2515 driver thread): copy and enqueue only. */
static void can_rx_callback(const struct device *dev, struct can_frame *frame, void *user_data)
{
    ARG_UNUSED(dev);
    struct rx_item item = {.frame = *frame, .bus = (uint8_t)(uintptr_t)user_data,
                           .received_ms = k_uptime_get_32()};
    if (k_msgq_put(&rx_queue, &item, K_NO_WAIT) != 0) atomic_inc(&rx_dropped);
}

static void can_state_callback(const struct device *dev, enum can_state state,
                               struct can_bus_err_cnt err_cnt, void *user_data)
{
    ARG_UNUSED(dev); ARG_UNUSED(err_cnt);
    unsigned bus = (unsigned)(uintptr_t)user_data;
    atomic_set(&can_state[bus], state);
    atomic_inc(&can_state_changes[bus]);
}

static void handle_ctrl(const struct can_frame *f)
{
    struct lab3_ctrl c;
    if (!lab3_ctrl_decode(f, &c)) {
        bad_input(FAULT_BAD_CTRL);
        return;
    }
    k_mutex_lock(&state_lock, K_FOREVER);
    command = c;
    zone_monitor_ctrl(&monitor);
    k_mutex_unlock(&state_lock);
    k_sem_give(&actuator_wake);
    refresh_state(); /* the first fresh CTRL may end the error state */
}

static void handle_fault(const struct can_frame *f)
{
    uint8_t reason = f->data[2];
    if (reason == FAULT_ZONE_LOST) return; /* informational; HB_MON detects loss locally */
    set_latch(reason != FAULT_CLEAR);
    refresh_state();
}

/* The one dispatch path: record per-bus traffic (R4.7 counts any frame from
 * another node, including our own frames that N2 relays back) and heartbeats,
 * validate, drop our own frames, drop the duplicate copy by (ID, source, seq),
 * hand first copies to RELAY, then to the tasks. */
static void dispatch(const struct rx_item *item)
{
    const struct can_frame *f = &item->frame;
    lab3_trace_toggle(item->bus == 0 ? TP_CAN_RX_A : TP_CAN_RX_B);
    uint8_t hb_zone = lab3_heartbeat_zone(f->id);
    bool valid = lab3_frame_valid(f);
    bool own = valid && lab3_frame_origin(f) == MY_ZONE;
    k_mutex_lock(&state_lock, K_FOREVER);
    zone_monitor_traffic(&monitor, item->bus, item->received_ms);
    if (valid && !own && hb_zone) zone_monitor_heartbeat(&monitor, hb_zone, item->bus, item->received_ms);
    k_mutex_unlock(&state_lock);
    if (!valid) {
        atomic_inc(&bad_crc);
        if (f->id == ID_CTRL) bad_input(FAULT_BAD_CRC);
        return;
    }
    if (own) return;
    struct frame_key key = {.id = (uint16_t)f->id, .source = lab3_dedup_source(f), .seq = f->data[0] & 0x0F};
    k_mutex_lock(&history_lock, K_FOREVER);
    enum frame_observation seen = frame_observe(&history, key, item->bus, item->received_ms);
    k_mutex_unlock(&history_lock);
    if (seen != FRAME_NEW) {
        atomic_inc(seen == FRAME_DUPLICATE ? &duplicates : &rx_dropped);
        return;
    }
#if defined(CONFIG_LAB3_RELAY)
    /* Relay before local processing: the forwarded copy is on N3's brake path. */
    if (k_msgq_put(&relay_queue, item, K_NO_WAIT) != 0) atomic_inc(&relay_dropped);
#endif
    switch (f->id) {
    case ID_CTRL:
        handle_ctrl(f);
        break;
    case ID_BLINK:
        k_mutex_lock(&state_lock, K_FOREVER);
        blink_mode = f->data[1];
        blink_phase = f->data[2] & 1;
        blink_seen = true;
        blink_ms = item->received_ms;
        blink_count++;
        k_mutex_unlock(&state_lock);
        k_sem_give(&blink_wake);
        break;
    case ID_FAULT:
        handle_fault(f);
        break;
    default: /* heartbeats recorded above; FORCE is for N1 */
        break;
    }
}

static void rx_dispatch_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    struct rx_item item;
    while (true) {
        k_mutex_lock(&state_lock, K_FOREVER);
        uint32_t wait_ms = zone_monitor_next_change_ms(&monitor, k_uptime_get_32());
        k_mutex_unlock(&state_lock);
        if (k_msgq_get(&rx_queue, &item, wait_ms == UINT32_MAX ? K_FOREVER : K_MSEC(wait_ms)) != 0) {
            refresh_state(); /* a bus just reached 60 ms of silence: DEG_x now, not at HB_MON */
            continue;
        }
        enum lab3_timing_id task = item.bus == 0 ? T_RX_DISPATCH_A : T_RX_DISPATCH_B;
        uint32_t start = lab3_task_start(task);
        dispatch(&item);
        lab3_timing_end(T_RX_DISPATCH, start);
        lab3_task_end(task, start);
    }
}
K_THREAD_DEFINE(rx_dispatch_tid, 2048, rx_dispatch_thread, NULL, NULL, NULL, 1, 0, 0);

#if defined(CONFIG_LAB3_RELAY)
/* RELAY (N2 only, priority 2): forward each foreign first copy to the other bus
 * immediately unless that bus already delivered it. No fault detection gates
 * it, so scenario (c) has no 60 ms gap. History claims make it loop-free. */
static void relay_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    struct rx_item item;
    while (true) {
        if (k_msgq_get(&relay_queue, &item, K_FOREVER) != 0) continue;
        uint32_t start = lab3_task_start(T_RELAY);
        struct frame_key key = {.id = (uint16_t)item.frame.id,
            .source = lab3_dedup_source(&item.frame), .seq = item.frame.data[0] & 0x0F};
        k_mutex_lock(&history_lock, K_FOREVER);
        enum relay_claim claim = frame_claim_relay(&history, key, item.bus, item.received_ms,
                                                   k_uptime_get_32());
        k_mutex_unlock(&history_lock);
        if (claim == RELAY_SEND) {
            int rc = submit(item.bus ^ 1U, &item.frame, K_MSEC(1));
            lab3_trace_toggle(TP_RELAY_TX); /* clarification #6: after the send returns */
            atomic_inc(rc == 0 ? &relay_sent : &relay_failed);
        } else if (claim == RELAY_STALE) {
            atomic_inc(&relay_stale);
        }
        lab3_task_end(T_RELAY, start);
    }
}
K_THREAD_DEFINE(relay_tid, 1536, relay_thread, NULL, NULL, NULL, 2, 0, 0);
#endif

/* STEER (N2) / DRIVE (N3): apply the latest command or the error fail-safe.
 * N2: SRV follows CTRL, also in the system error state (R3); only when this
 * zone itself failed (own test press or isolation) does it hold the last pulse
 * (R4.7 "steering held"). No pulse until the first valid CTRL.
 * N3: DIR_A high selects forward and PWM_OUT carries throttle duty; brake or
 * error drops DIR_A and holds PWM_OUT high (L298 enable-high, equal-input brake). */
static void actuator_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    while (true) {
        k_sem_take(&actuator_wake, K_FOREVER);
        k_mutex_lock(&state_lock, K_FOREVER);
        struct lab3_ctrl now = command;
        bool error = zone_error, failed = zone_failed, commanded = monitor.ctrl_seen;
        k_mutex_unlock(&state_lock);
        uint32_t start = lab3_task_start(T_STEER_DRIVE);
#if defined(CONFIG_LAB3_ZONE_N2)
        ARG_UNUSED(error);
        lab3_trace_set(TP_STEER, 1);
        if (commanded && !failed)
            (void)pwm_set_dt(&actuator_pwm, ACTUATOR_PERIOD, PWM_USEC(lab3_steering_pulse(now.steer)));
        lab3_trace_set(TP_STEER, 0);
#else
        ARG_UNUSED(failed); ARG_UNUSED(commanded);
        if (error || now.brake > 0) {
            lab3_trace_set(TP_DIR_A, 0);
            (void)pwm_set_dt(&actuator_pwm, ACTUATOR_PERIOD, ACTUATOR_PERIOD);
        } else {
            (void)pwm_set_dt(&actuator_pwm, ACTUATOR_PERIOD, ACTUATOR_PERIOD / 100U * now.throttle);
            lab3_trace_set(TP_DIR_A, 1);
        }
        lab3_trace_toggle(TP_PWM_SET); /* as Lab 2: just after the timer write */
#endif
        lab3_task_end(T_STEER_DRIVE, start);
    }
}
K_THREAD_DEFINE(actuator_tid, 1024, actuator_thread, NULL, NULL, NULL, 3, 0, 0);

/* BLINK_F / BLINK_R: drive lamps on BLINK reception so both zones switch on the
 * same message (front/rear sync). In the error state hazards start at once on
 * a local 500 ms timer (an isolated zone must flash within 100 ms, R4.7); each
 * hazard BLINK from N1 re-phases that timer, so both zones flash in unison and
 * keep flashing if N1's BLINKs stop. */
static void blink_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    int64_t next_local_edge = 0;
    bool local_on = false, local_running = false;
    uint32_t synced_count = 0;
    k_timeout_t timeout = K_NO_WAIT;
    while (true) {
        k_sem_take(&blink_wake, timeout);
        uint32_t start = lab3_task_start(T_BLINK);
        int64_t now = k_uptime_get();
        k_mutex_lock(&state_lock, K_FOREVER);
        uint8_t mode = blink_mode, phase = blink_phase;
        uint32_t age = (uint32_t)now - blink_ms, count = blink_count;
        bool fresh = blink_seen && age < BLINK_TIMEOUT_MS;
        bool error = zone_error;
        k_mutex_unlock(&state_lock);
        bool left, right;
        if (error) {
            if (fresh && mode == BLINK_HAZARD) {
                if (!local_running || count != synced_count) {
                    local_on = phase;
                    next_local_edge = now + (BLINK_HALF_PERIOD_MS - MIN(age, BLINK_HALF_PERIOD_MS));
                    synced_count = count;
                }
            } else if (!local_running) {
                local_on = true;
                next_local_edge = now + BLINK_HALF_PERIOD_MS;
            }
            local_running = true;
            if (now >= next_local_edge) {
                local_on = !local_on;
                next_local_edge += BLINK_HALF_PERIOD_MS;
                if (next_local_edge <= now) next_local_edge = now + BLINK_HALF_PERIOD_MS;
            }
            left = right = local_on;
            timeout = K_TIMEOUT_ABS_MS(next_local_edge);
        } else {
            local_running = false;
            if (!fresh) mode = BLINK_OFF;
            left = phase && (mode == BLINK_LEFT || mode == BLINK_HAZARD);
            right = phase && (mode == BLINK_RIGHT || mode == BLINK_HAZARD);
            timeout = fresh ? K_TIMEOUT_ABS_MS(now + (BLINK_TIMEOUT_MS - age)) : K_FOREVER;
        }
        lab3_trace_set(TP_LEFT, left);
        lab3_trace_set(TP_RIGHT, right);
        lab3_task_end(T_BLINK, start);
    }
}
K_THREAD_DEFINE(blink_tid, 1024, blink_thread, NULL, NULL, NULL, 2, 0, 0);

/* GPIO ISR only wakes TEST_BTN; debounce, state and CAN TX run in the thread. */
static struct gpio_callback button_callback;
static void button_isr(const struct device *port, struct gpio_callback *cb, gpio_port_pins_t pins)
{
    ARG_UNUSED(port); ARG_UNUSED(cb); ARG_UNUSED(pins);
    k_sem_give(&button_wake);
}

/* TEST_BTN: single press latches error, sends one FAULT and stops this node's
 * heartbeats; a second press within 500 ms clears every zone's latch with a
 * FAULT clear and resumes them. */
static void button_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    bool stable = gpio_pin_get_dt(&test_button) > 0;
    uint32_t last_press_ms = 0, last_edge_ms = 0;
    bool armed = false, pressed_before = false;
    while (true) {
        k_sem_take(&button_wake, K_FOREVER);
        k_msleep(DEBOUNCE_MS);
        bool pressed = gpio_pin_get_dt(&test_button) > 0;
        if (pressed == stable) continue; /* bounce or coalesced edge */
        stable = pressed;
        if (!pressed) continue;
        uint32_t now = k_uptime_get_32();
        /* Measured from the previous raw press, so chatter never adds up to a second press. */
        bool same_press = pressed_before && (uint32_t)(now - last_edge_ms) < SINGLE_PRESS_MS;
        last_edge_ms = now;
        pressed_before = true;
        if (same_press) continue;
        uint32_t start = lab3_task_start(T_TEST_BTN);
        bool clear = armed && (uint32_t)(now - last_press_ms) <= DOUBLE_PRESS_MS;
        set_latch(!clear);
        if (!clear) {
            k_mutex_lock(&state_lock, K_FOREVER);
            hb_silenced = true;
            k_mutex_unlock(&state_lock);
        }
        refresh_state();
        send_fault(MY_ZONE, clear ? FAULT_CLEAR : FAULT_TEST_BUTTON);
        armed = !clear;
        last_press_ms = now;
        lab3_task_end(T_TEST_BTN, start);
    }
}
K_THREAD_DEFINE(button_tid, 1024, button_thread, NULL, NULL, NULL, 4, 0, 0);

#if defined(CONFIG_LAB3_ZONE_N3)
/* PID: Lab 2 velocity calculation on synthetic samples every 10 ms. There are
 * no encoders in this lab, so DRIVE applies throttle duty directly. */
static void pid_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    struct lab3_pid_measurement pid;
    lab3_pid_measurement_init(&pid);
    int64_t next = k_uptime_get();
    while (true) {
        uint32_t start = lab3_task_start(T_PID);
        lab3_trace_set(TP_PID, 1);
        struct lab3_pid_result result = lab3_pid_measurement_step(&pid);
        lab3_trace_set(TP_PID, 0);
        lab3_task_end(T_PID, start);
        __ASSERT(result.status == 0, "Synthetic Lab 2 PID calculation failed");
        ARG_UNUSED(result);
        periodic_wait(&next, 10);
    }
}
K_THREAD_DEFINE(pid_tid, 1024, pid_thread, NULL, NULL, NULL, 5, 0, 0);
#endif

/* The MCP2515 INT line is edge-triggered in Zephyr. An edge missed while INT is
 * already low (seen twice as a dead CAN B on Oct 21) leaves the controller
 * unserviced forever. INT held low across two 20 ms checks cannot be a pending
 * frame, so pend the EXTI line in software to rerun the driver's handler. */
static void kick_stuck_int(bool *was_active)
{
    for (unsigned bus = 0; bus < 2; ++bus) {
        bool active = gpio_pin_get_dt(&can_int[bus]) > 0;
        if (active && was_active[bus]) {
            EXTI->SWIER = BIT(can_int[bus].pin);
            atomic_inc(&int_kicks[bus]);
        }
        was_active[bus] = active;
    }
}

/* HB_MON: every 20 ms, per-bus liveness to DEG_A/DEG_B, error state to ERR,
 * FAULT on a peer zone's failure, and the only watchdog feed. */
static void monitor_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    bool was_alive[ZONE_SLOTS] = {false};
    bool int_was_active[2] = {false};
    int64_t next = k_uptime_get();
    while (true) {
        uint32_t start = lab3_task_start(T_HB_MON);
        struct zone_health h = refresh_state();
        for (uint8_t zone = ZONE_N1; zone <= ZONE_N3; ++zone) {
            if (zone == MY_ZONE) continue;
            if (was_alive[zone] && !h.alive[zone]) send_fault(zone, FAULT_ZONE_LOST);
            was_alive[zone] = h.alive[zone];
        }
        kick_stuck_int(int_was_active);
        (void)wdt_feed(watchdog_dev, watchdog_channel);
        lab3_task_end(T_HB_MON, start);
        periodic_wait(&next, HB_PERIOD_MS);
    }
}
K_THREAD_DEFINE(hb_mon_tid, 1024, monitor_thread, NULL, NULL, NULL, 6, 0, 0);

/* HB_TX: zone state and per-bus health every 20 ms, except while silenced by
 * this node's test button. */
static void heartbeat_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    int64_t next = k_uptime_get();
    while (true) {
        uint32_t start = lab3_task_start(T_HB_TX);
        k_mutex_lock(&state_lock, K_FOREVER);
        struct zone_health h = zone_monitor_evaluate(&monitor, k_uptime_get_32());
        bool error = zone_error, silenced = hb_silenced;
        k_mutex_unlock(&state_lock);
        if (!silenced) {
            struct can_frame f;
            lab3_pack_heartbeat(&f, MY_HB_ID, error ? STATE_ERROR : STATE_OK, h.bus_ok[0], h.bus_ok[1]);
            send_both(&f);
        }
        lab3_task_end(T_HB_TX, start);
        periodic_wait(&next, HB_PERIOD_MS);
    }
}
K_THREAD_DEFINE(hb_tx_tid, 1024, heartbeat_thread, NULL, NULL, NULL, 7, 0, 0);

#if defined(CONFIG_LAB3_ZONE_N2)
/* FORCE_TX: dummy signed counter every 50 ms (no force feedback this lab). */
static void force_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    int8_t counter = 0;
    int64_t next = k_uptime_get();
    while (true) {
        uint32_t start = lab3_task_start(T_FORCE_TX);
        struct can_frame f;
        lab3_pack_force(&f, counter++);
        send_both(&f);
        lab3_task_end(T_FORCE_TX, start);
        periodic_wait(&next, 50);
    }
}
K_THREAD_DEFINE(force_tid, 1024, force_thread, NULL, NULL, NULL, 8, 0, 0);
#endif

/* Low-priority console every 5 s; nothing prints on the receive path. */
static void diagnostics_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    wait_ready();
    while (true) {
        k_msleep(5000);
        k_mutex_lock(&state_lock, K_FOREVER);
        struct zone_health h = zone_monitor_evaluate(&monitor, k_uptime_get_32());
        struct lab3_ctrl ctrl = command;
        bool latched = monitor.latched, silenced = hb_silenced, commanded = monitor.ctrl_seen;
        k_mutex_unlock(&state_lock);
        printk("%s state=%s latched=%d hb_silenced=%d isolated=%d alive=N1:%d,N2:%d,N3:%d deg_a=%d deg_b=%d "
               "ctrl_seen=%d steer=%d throttle=%u brake=%u\n", APP_NAME, h.error ? "ERROR" : "OK",
               latched, silenced, h.isolated,
               h.alive[1], h.alive[2], h.alive[3], h.degraded[0], h.degraded[1], commanded,
               ctrl.steer, ctrl.throttle, ctrl.brake);
        printk("CAN state_a=%d state_b=%d changes_a=%d changes_b=%d int_kicks_a=%d int_kicks_b=%d "
               "rx_dropped=%d dup=%d bad_crc=%d\n",
               (int)atomic_get(&can_state[0]), (int)atomic_get(&can_state[1]),
               (int)atomic_get(&can_state_changes[0]), (int)atomic_get(&can_state_changes[1]),
               (int)atomic_get(&int_kicks[0]), (int)atomic_get(&int_kicks[1]),
               (int)atomic_get(&rx_dropped), (int)atomic_get(&duplicates), (int)atomic_get(&bad_crc));
        printk("TX_COUNTS rejected_a=%d rejected_b=%d completed_a=%d completed_b=%d failed_a=%d failed_b=%d\n",
               (int)atomic_get(&tx_rejected[0]), (int)atomic_get(&tx_rejected[1]),
               (int)atomic_get(&tx_completed[0]), (int)atomic_get(&tx_completed[1]),
               (int)atomic_get(&tx_failed[0]), (int)atomic_get(&tx_failed[1]));
#if defined(CONFIG_LAB3_RELAY)
        printk("RELAY sent=%d failed=%d stale=%d queue_dropped=%d\n", (int)atomic_get(&relay_sent),
               (int)atomic_get(&relay_failed), (int)atomic_get(&relay_stale), (int)atomic_get(&relay_dropped));
#endif
        for (int id = 0; id < T_COUNT; ++id) {
            uint32_t count = lab3_timing_count(id);
            if (count == 0) continue;
            uint32_t cycles = lab3_timing_max_cycles(id);
            printk("OBS_TASK zone=%s uptime_ms=%u name=%s max_cycles=%u max_us=%u count=%u\n",
                   MY_ZONE == ZONE_N2 ? "N2" : "N3", k_uptime_get_32(), lab3_timing_name(id),
                   cycles, k_cyc_to_us_ceil32(cycles), count);
        }
    }
}
K_THREAD_DEFINE(diag_tid, 1536, diagnostics_thread, NULL, NULL, NULL, 10, 0, 0);

static int setup_can(unsigned bus)
{
    const struct device *dev = can_dev[bus];
    if (!device_is_ready(dev)) { printk("CAN %c not ready\n", 'A' + bus); return -ENODEV; }
    can_set_state_change_callback(dev, can_state_callback, (void *)(uintptr_t)bus);
    int rc = can_start(dev);
    if (rc && rc != -EALREADY) { printk("can_start %c failed: %d\n", 'A' + bus, rc); return rc; }
    for (unsigned i = 0; i < ARRAY_SIZE(catalog_ids); ++i) {
        struct can_filter filter = {.id = catalog_ids[i], .mask = CAN_STD_ID_MASK};
        rc = can_add_rx_filter(dev, can_rx_callback, (void *)(uintptr_t)bus, &filter);
        if (rc < 0) { printk("CAN %c filter 0x%03x failed: %d\n", 'A' + bus, catalog_ids[i], rc); return rc; }
    }
    return 0;
}

static int setup_button(void)
{
    if (!gpio_is_ready_dt(&test_button)) return -ENODEV;
    int rc = gpio_pin_configure_dt(&test_button, GPIO_INPUT);
    if (rc) return rc;
    gpio_init_callback(&button_callback, button_isr, BIT(test_button.pin));
    rc = gpio_add_callback(test_button.port, &button_callback);
    return rc ? rc : gpio_pin_interrupt_configure_dt(&test_button, GPIO_INT_EDGE_BOTH);
}

static int setup_watchdog(void)
{
    if (!device_is_ready(watchdog_dev)) return -ENODEV;
    struct wdt_timeout_cfg cfg = {.window = {.min = 0, .max = 1000}, .flags = WDT_FLAG_RESET_SOC};
    watchdog_channel = wdt_install_timeout(watchdog_dev, &cfg);
    if (watchdog_channel < 0) return watchdog_channel;
    return wdt_setup(watchdog_dev, 0);
}

int main(void)
{
    zone_monitor_init(&monitor, MY_ZONE, k_uptime_get_32());
    int rc = lab3_trace_init();
    if (rc) { printk("Test-point GPIO setup failed: %d\n", rc); return rc; }
    lab3_trace_set(TP_ERR, 1); /* power-up in error */
    if (!pwm_is_ready_dt(&actuator_pwm)) { printk("PWM not ready\n"); return -ENODEV; }
#if defined(CONFIG_LAB3_ZONE_N3)
    (void)pwm_set_dt(&actuator_pwm, ACTUATOR_PERIOD, ACTUATOR_PERIOD); /* braked */
#else
    (void)pwm_set_dt(&actuator_pwm, ACTUATOR_PERIOD, 0); /* servo off */
#endif
    rc = setup_button();
    if (rc) { printk("Test button setup failed: %d\n", rc); return rc; }
    for (unsigned bus = 0; bus < 2; ++bus) {
        rc = setup_can(bus);
        if (rc) return rc;
    }
    rc = setup_watchdog();
    if (rc) { printk("IWDG setup failed: %d\n", rc); return rc; }
    printk("%s Lab 3 demo online: CAN A/B 500 kbit/s, relay=%d, swap_ab=%d, SPI request %u Hz\n",
           APP_NAME, IS_ENABLED(CONFIG_LAB3_RELAY), IS_ENABLED(CONFIG_LAB3_SWAP_CAN_AB),
           (unsigned)DT_PROP(DT_NODELABEL(can_a), spi_max_frequency));
    lab3_probe_ready();
    k_event_post(&app_ready, BIT(0));
    return 0;
}
