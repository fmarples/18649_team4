/*
 * Lab 3 demo firmware for either NUCLEO-F401RE.
 * Build once with -DCONFIG_LAB3_ZONE_N2=y (front) and once with N3 (rear).
 * This firmware deliberately drives LEDs/GPIO test points only; no servo or H-bridge.
 */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/can.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/watchdog.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>
#include <zephyr/sys/byteorder.h>
#include <string.h>
#include <stdio.h>
#include "can_protocol.h"
#include "timing_trace.h"
#include "timing_stats.h"

#if defined(CONFIG_LAB3_ZONE_N2) && defined(CONFIG_LAB3_ZONE_N3)
#error "Choose exactly one zone: N2 front or N3 rear"
#endif
#if !defined(CONFIG_LAB3_ZONE_N2) && !defined(CONFIG_LAB3_ZONE_N3)
#error "Set CONFIG_LAB3_ZONE_N2=y or CONFIG_LAB3_ZONE_N3=y in prj.conf"
#endif
#if defined(CONFIG_LAB3_ZONE_N2)
#define MY_ZONE ZONE_N2
#define MY_HB_ID ID_HB_N2
#define APP_NAME "N2 FRONT"
#else
#define MY_ZONE ZONE_N3
#define MY_HB_ID ID_HB_N3
#define APP_NAME "N3 REAR"
#endif

#define HB_PERIOD_MS 20
#define HB_FAIL_MS 60 /* three missed 20 ms heartbeats on BOTH buses */
#define DEBOUNCE_MS 2
#define DOUBLE_PRESS_MS 400
#define QUEUE_DEPTH 32

static const struct device *const can_a = DEVICE_DT_GET(DT_NODELABEL(can_a));
static const struct device *const can_b = DEVICE_DT_GET(DT_NODELABEL(can_b));
static const struct gpio_dt_spec test_button = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), test_button_gpios);

struct rx_item { struct can_frame frame; uint8_t bus; uint32_t received_ms; };
K_MSGQ_DEFINE(rx_queue, sizeof(struct rx_item), QUEUE_DEPTH, 4);
#if defined(CONFIG_LAB3_ZONE_N2)
K_MSGQ_DEFINE(relay_queue, sizeof(struct rx_item), 16, 4);
static atomic_t relay_overflow;
#endif
K_MUTEX_DEFINE(state_lock);
K_SEM_DEFINE(test_button_event, 0, 1);
static struct gpio_callback test_button_callback;
static bool button_stable;

struct node_state {
    int16_t steer;
    uint8_t throttle, brake, buttons;
    uint8_t blink_mode, blink_phase;
    uint32_t ctrl_seq, last_ctrl_ms;
    uint32_t last_hb_ms[4][2];
    bool hb_seen[4][2];
    bool peer_error[4];
    bool error, manual_error, have_ctrl, has_been_ready;
    uint8_t force_counter;
    uint32_t rx_count, duplicate_count, bad_crc_count, relay_count;
} s = {.error=true};

static const uint32_t catalog_ids[] = {ID_CTRL, ID_FAULT, ID_HB_N1, ID_HB_N2, ID_HB_N3, ID_BLINK, ID_FORCE};
static int filter_ids[2][7];
static uint8_t tx_seq[0x301]; /* Only IDs in catalog are indexed; sparse but simple and small. */
/* Track sequence history independently per bus. A same-sequence frame on the SAME
 * bus is not treated as a duplicate: the 4-bit sequence wraps, and a same-bus
 * repeat may be a legitimate new frame. Only a matching opposite-bus copy seen
 * within the bounded dual-send window is suppressed from application processing.
 */
#define DUP_WINDOW_MS 5U
static uint8_t last_seq[7][2];
static uint32_t last_seq_ms[7][2];
static bool seen_seq_valid[7][2];
static uint8_t seen_fault_source[7][2];
static atomic_t rx_overflow;
static const struct device *const watchdog_dev = DEVICE_DT_GET(DT_NODELABEL(iwdg));
static int watchdog_channel = -1;
static uint32_t last_press_ms = 0;

static int catalog_index(uint32_t id) {
    for (unsigned i=0; i<ARRAY_SIZE(catalog_ids); ++i) if (catalog_ids[i] == id) return (int)i;
    return -1;
}
static uint8_t source_key(const struct can_frame *f) { return f->id == ID_FAULT ? f->data[1] : 0; }
static uint8_t next_seq(uint32_t id) {
    k_mutex_lock(&state_lock, K_FOREVER);
    uint8_t value = tx_seq[id] & 0x0F; tx_seq[id] = (value + 1) & 0x0F;
    k_mutex_unlock(&state_lock);
    return value;
}
/* Keep periodic task releases phase-locked instead of adding WCET to every period. */
static void periodic_wait(int64_t *next_release_ms, uint32_t period_ms) {
    *next_release_ms += period_ms;
    int64_t now = k_uptime_get();
    if (*next_release_ms <= now) {
        int64_t missed = (now - *next_release_ms) / period_ms + 1;
        *next_release_ms += missed * period_ms;
    }
    int64_t delay = *next_release_ms - now;
    if (delay > 0) k_msleep((int32_t)delay);
}

/* Queues one frame to a specific controller. Called from worker/task context only. */
static int send_one(unsigned bus, const struct can_frame *frame) {
    uint32_t start = lab3_timing_start();
    lab3_trace_toggle(bus == 0 ? 2 : 3);
    const struct device *dev = bus == 0 ? can_a : can_b;
    int rc = can_send(dev, frame, K_MSEC(2), NULL, NULL);
    lab3_timing_end(T_CAN_TX, start);
    return rc;
}
/* Lab 3 normal sender: one sequence increment per logical frame, sent on A and B. */
static void send_both(struct can_frame *frame) {
    (void)send_one(0, frame);
    (void)send_one(1, frame);
}
static void send_fault(uint8_t reason) {
    struct can_frame f;
    lab3_pack_fault(&f, next_seq(ID_FAULT), MY_ZONE, reason);
    send_both(&f);
}

/* CAN driver callback: no printk, allocation, locks, or CAN transmission here. */
static void can_rx_callback(const struct device *dev, struct can_frame *frame, void *user_data) {
    ARG_UNUSED(dev);
    unsigned bus = (unsigned)(uintptr_t)user_data;
    struct rx_item item = {.frame=*frame, .bus=(uint8_t)bus, .received_ms=k_uptime_get_32()};
    if (k_msgq_put(&rx_queue, &item, K_NO_WAIT) != 0) {
        /* Callback stays nonblocking; the dispatch thread purges stale backlog. */
        atomic_set(&rx_overflow, 1);
    }
}

/* Suppress only a matching copy received on the opposite bus within DUP_WINDOW_MS.
 * Per-bus history avoids incorrectly dropping a legitimate same-bus frame merely
 * because its 4-bit sequence matches the last frame (including after wraparound).
 * Tune DUP_WINDOW_MS only after checking measured cross-bus arrival skew on hardware.
 */
static bool first_copy(const struct rx_item *item) {
    int i = catalog_index(item->frame.id);
    if (i < 0 || item->bus > 1) return false;
    const uint8_t seq = item->frame.data[0] & 0x0F;
    const uint8_t source = source_key(&item->frame);
    const unsigned bus = item->bus;
    const unsigned other = bus ^ 1U;
    const uint32_t now = item->received_ms;
    const bool opposite_match = seen_seq_valid[i][other] &&
        last_seq[i][other] == seq && seen_fault_source[i][other] == source &&
        (uint32_t)(now - last_seq_ms[i][other]) <= DUP_WINDOW_MS;

    seen_seq_valid[i][bus] = true;
    last_seq[i][bus] = seq;
    last_seq_ms[i][bus] = now;
    seen_fault_source[i][bus] = source;

    if (opposite_match) {
        k_mutex_lock(&state_lock, K_FOREVER);
        s.duplicate_count++;
        k_mutex_unlock(&state_lock);
        return false;
    }
    return true;
}

static void mark_heartbeat(const struct can_frame *frame, uint8_t bus, uint32_t now) {
    int zone = frame->id == ID_HB_N1 ? ZONE_N1 : frame->id == ID_HB_N2 ? ZONE_N2 : ZONE_N3;
    if (zone < 1 || zone > 3) return;
    s.last_hb_ms[zone][bus] = now; s.hb_seen[zone][bus] = true;
    s.peer_error[zone] = frame->data[1] == STATE_ERROR;
}
static int source_zone_for_frame(const struct can_frame *f) {
    if (f->id == ID_HB_N1) return ZONE_N1;
    if (f->id == ID_HB_N2 || f->id == ID_FORCE) return ZONE_N2;
    if (f->id == ID_HB_N3) return ZONE_N3;
    if (f->id == ID_CTRL || f->id == ID_BLINK) return ZONE_N1;
    if (f->id == ID_FAULT && f->data[1] >= ZONE_N1 && f->data[1] <= ZONE_N3) return f->data[1];
    return 0;
}
/* Relay only after this source's heartbeat has disappeared from the opposite bus.
 * This avoids doubling every frame in the healthy dual-bus case. After three missed
 * heartbeats, the first bus still receiving that source forwards its messages. */
static bool should_relay(const struct rx_item *item) {
    int source = source_zone_for_frame(&item->frame);
    if (source < ZONE_N1 || source > ZONE_N3 || source == MY_ZONE) return false;
    unsigned opposite = item->bus == 0 ? 1 : 0;
    uint32_t now = k_uptime_get_32();
    k_mutex_lock(&state_lock, K_FOREVER);
    bool incoming_alive = s.hb_seen[source][item->bus] &&
        (uint32_t)(now-s.last_hb_ms[source][item->bus]) < HB_FAIL_MS;
    bool opposite_alive = s.hb_seen[source][opposite] &&
        (uint32_t)(now-s.last_hb_ms[source][opposite]) < HB_FAIL_MS;
    k_mutex_unlock(&state_lock);
    return incoming_alive && !opposite_alive;
}

/* Apply only validated frames. All state shared with monitor/diagnostics is mutex-protected. */
static void dispatch_frame_impl(struct rx_item *item) {
    struct can_frame *f = &item->frame;
    uint32_t now = item->received_ms;
    if (catalog_index(f->id) < 0) return;
    if (!lab3_frame_valid(f)) {
        k_mutex_lock(&state_lock, K_FOREVER); s.bad_crc_count++; s.error = true; if (f->id == ID_CTRL) s.manual_error = true; k_mutex_unlock(&state_lock);
        if (f->id == ID_CTRL) send_fault(2); /* reason 2: bad CRC */
        return;
    }
    /* Heartbeat reception is recorded per interface even when the payload is a duplicate.
     * Otherwise the healthy second bus would look silent after global deduplication. */
    if (f->id == ID_HB_N1 || f->id == ID_HB_N2 || f->id == ID_HB_N3) {
        k_mutex_lock(&state_lock, K_FOREVER); mark_heartbeat(f, item->bus, now); k_mutex_unlock(&state_lock);
    }
    bool first = first_copy(item);
    if (!first) return;

    /* N2 relay is a separate priority-2 thread. The RX dispatcher only enqueues candidates. */
#if defined(CONFIG_LAB3_ZONE_N2)
    if (k_msgq_put(&relay_queue, item, K_NO_WAIT) != 0) atomic_set(&relay_overflow, 1);
#endif

    bool bad_range = false;
    k_mutex_lock(&state_lock, K_FOREVER);
    s.rx_count++;
    if (f->id == ID_HB_N1 || f->id == ID_HB_N2 || f->id == ID_HB_N3) {
        /* Per-bus timestamp was updated above, before duplicate suppression. */
    } else if (f->id == ID_CTRL && (MY_ZONE == ZONE_N2 || MY_ZONE == ZONE_N3)) {
        int16_t steer = (int16_t)sys_get_le16(&f->data[1]);
        uint8_t throttle = f->data[3], brake = f->data[4], buttons = f->data[5];
        /* Demo input bounds; steering int16 is accepted, pedal fields are normalized percentages. */
        if ((f->data[0] >> 4) != 1 || f->data[6] != 0 || throttle > 100 || brake > 100) {
            s.error = true; s.manual_error = true; bad_range = true;
        } else {
            s.steer = steer; s.throttle = throttle; s.brake = brake; s.buttons = buttons;
            s.ctrl_seq = f->data[0] & 0x0F; s.last_ctrl_ms = now; s.have_ctrl = true;
        }
    } else if (f->id == ID_BLINK) {
        s.blink_mode = f->data[1]; s.blink_phase = f->data[2] & 1;
    } else if (f->id == ID_FAULT) {
        if (f->data[1] != MY_ZONE) {
            if (f->data[2] == 0) {
                s.manual_error = false; s.error = false;
                for (int zone=ZONE_N1; zone<=ZONE_N3; ++zone) s.peer_error[zone] = false;
            } else { s.error = true; s.manual_error = true; }
        }
    }
    k_mutex_unlock(&state_lock);
    if (bad_range) send_fault(3); /* reason 3: out-of-range CTRL */

#if defined(CONFIG_LAB3_ZONE_N2)
    if (f->id == ID_CTRL) {
        /* SRV probe wraps steering task body; demo prints the numeric request, no servo output. */
        uint32_t task_start = lab3_timing_start();
        lab3_trace_set(7, 1);
        k_mutex_lock(&state_lock, K_FOREVER); int16_t steer = s.steer; k_mutex_unlock(&state_lock);
        ARG_UNUSED(steer);
        lab3_trace_set(7, 0);
        lab3_timing_end(T_STEER_DRIVE, task_start);
    }
#else
    if (f->id == ID_CTRL) {
        uint32_t task_start = lab3_timing_start();
        /* DRIVE/PWM_SET and DIR_A are test points only: no H-bridge is initialized. */
        lab3_trace_set(8, 1);
        k_mutex_lock(&state_lock, K_FOREVER);
        uint8_t brake = s.brake;
        k_mutex_unlock(&state_lock);
        lab3_trace_set(9, brake > 0); /* DIR_A probe indicates requested brake in demo mode. */
        lab3_trace_set(8, 0);
        lab3_timing_end(T_STEER_DRIVE, task_start);
    }
#endif
}
static void dispatch_frame(struct rx_item *item) {
    lab3_trace_toggle(item->bus == 0 ? 0 : 1); /* CAN_RX_A/B after driver read, before app dispatch. */
    uint32_t start = lab3_timing_start();
    dispatch_frame_impl(item);
    lab3_timing_end(T_RX_DISPATCH, start);
}

static void rx_dispatch_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    struct rx_item item;
    while (true) {
        if (k_msgq_get(&rx_queue, &item, K_FOREVER) != 0) continue;
        if (atomic_cas(&rx_overflow, 1, 0)) {
            k_msgq_purge(&rx_queue);
            k_mutex_lock(&state_lock, K_FOREVER); s.error = true; s.manual_error = true; k_mutex_unlock(&state_lock);
            continue; /* Never apply a queued command after receive backlog overflow. */
        }
        dispatch_frame(&item);
    }
}
K_THREAD_DEFINE(rx_dispatch_tid, 2048, rx_dispatch_thread, NULL, NULL, NULL, 1, 0, 0);

#if defined(CONFIG_LAB3_ZONE_N2)
/* RELAY: own high-priority thread. Only forward when that source's heartbeat is absent on the other bus. */
static void relay_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    struct rx_item item;
    while (true) {
        if (k_msgq_get(&relay_queue, &item, K_FOREVER) != 0) continue;
        if (!should_relay(&item)) continue;
        uint32_t start = lab3_timing_start();
        lab3_trace_toggle(15); /* Dedicated N2 RELAY_TX test pin. */
        struct can_frame forwarded = item.frame;
        if (send_one(item.bus == 0 ? 1 : 0, &forwarded) == 0) {
            k_mutex_lock(&state_lock, K_FOREVER); s.relay_count++; k_mutex_unlock(&state_lock);
        }
        lab3_timing_end(T_RELAY, start);
    }
}
K_THREAD_DEFINE(relay_tid, 1536, relay_thread, NULL, NULL, NULL, 2, 0, 0);
#endif

/* HB_TX: periodic 20 ms task, frame sequence is incremented once per logical message. */
static void heartbeat_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    int64_t next_release_ms = k_uptime_get();
    while (true) {
        uint32_t task_start = lab3_timing_start();
        uint32_t now = k_uptime_get_32();
        k_mutex_lock(&state_lock, K_FOREVER);
        bool err = s.error || s.manual_error;
        bool bus_a = false, bus_b = false;
        for (int zone=ZONE_N1; zone<=ZONE_N3; ++zone) {
            if (zone == MY_ZONE) continue;
            bus_a |= s.hb_seen[zone][0] && (uint32_t)(now-s.last_hb_ms[zone][0]) < HB_FAIL_MS;
            bus_b |= s.hb_seen[zone][1] && (uint32_t)(now-s.last_hb_ms[zone][1]) < HB_FAIL_MS;
        }
        k_mutex_unlock(&state_lock);
        struct can_frame f;
        lab3_pack_heartbeat(&f, MY_HB_ID, next_seq(MY_HB_ID), err ? STATE_ERROR : STATE_OK, bus_a, bus_b);
        send_both(&f);
        lab3_timing_end(T_HB_TX, task_start);
        periodic_wait(&next_release_ms, HB_PERIOD_MS);
    }
}
K_THREAD_DEFINE(hb_tx_tid, 1024, heartbeat_thread, NULL, NULL, NULL, 4, 0, 0);

#if defined(CONFIG_LAB3_ZONE_N2)
/* FORCE_TX: dummy signed counter every 50 ms; not actual force feedback. */
static void force_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    int64_t next_release_ms = k_uptime_get();
    while (true) {
        struct can_frame f; k_mutex_lock(&state_lock, K_FOREVER); int8_t count = (int8_t)++s.force_counter; k_mutex_unlock(&state_lock);
        lab3_pack_force(&f, next_seq(ID_FORCE), count); send_both(&f); periodic_wait(&next_release_ms, 50);
    }
}
K_THREAD_DEFINE(force_tx_tid, 1024, force_thread, NULL, NULL, NULL, 5, 0, 0);
#endif

/* HB_MON: degraded per-bus LEDs and error-state supervision (3 missed heartbeats). */
static void monitor_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (true) {
        uint32_t task_start = lab3_timing_start();
        uint32_t now = k_uptime_get_32();
        bool bus_healthy[2] = {false,false};
        bool bus_seen[2] = {false,false};
        bool all_peers_alive = true;
        bool any_peer_error = false;
        k_mutex_lock(&state_lock, K_FOREVER);
        for (int zone=ZONE_N1; zone<=ZONE_N3; ++zone) {
            if (zone == MY_ZONE) continue;
            bool alive_a = s.hb_seen[zone][0] && (uint32_t)(now-s.last_hb_ms[zone][0]) < HB_FAIL_MS;
            bool alive_b = s.hb_seen[zone][1] && (uint32_t)(now-s.last_hb_ms[zone][1]) < HB_FAIL_MS;
            bus_healthy[0] |= alive_a; bus_healthy[1] |= alive_b;
            bus_seen[0] |= s.hb_seen[zone][0]; bus_seen[1] |= s.hb_seen[zone][1];
            if (!alive_a && !alive_b) all_peers_alive = false;
            any_peer_error |= s.peer_error[zone];
        }
        if (atomic_get(&rx_overflow)) { s.error = true; s.manual_error = true; }
        /* Require a fresh command stream as well as peer heartbeats. N1's stale-input
         * policy sends a safe command; this guard also covers a silent/broken N1. */
        const bool ctrl_fresh = s.have_ctrl && (uint32_t)(now - s.last_ctrl_ms) < 60U;
        if (s.has_been_ready && !ctrl_fresh) s.error = true;
#if defined(CONFIG_LAB3_ZONE_N2)
        if (atomic_cas(&relay_overflow, 1, 0)) { s.error = true; s.manual_error = true; }
#endif
        if (!all_peers_alive || any_peer_error) s.error = true;
        if (all_peers_alive && ctrl_fresh && !s.manual_error) {
            /* Cold-start ERROR may clear once the graph is complete; a stale CTRL or
             * remote ERROR keeps the node fail-safe until fresh traffic/clear arrives. */
            if (!s.has_been_ready || !any_peer_error) s.error = false;
            s.has_been_ready = true;
        }
        bool err = s.error || s.manual_error;
        k_mutex_unlock(&state_lock);
        lab3_trace_set(4, bus_seen[0] && !bus_healthy[0]); lab3_trace_set(5, bus_seen[1] && !bus_healthy[1]); lab3_trace_set(6, err);
        /* Feed IWDG only from the periodic supervisor; a wedged supervisor resets the MCU. */
        if (watchdog_channel >= 0) (void)wdt_feed(watchdog_dev, watchdog_channel);
        lab3_timing_end(T_HB_MON, task_start);
        k_msleep(5);
    }
}
K_THREAD_DEFINE(hb_mon_tid, 1024, monitor_thread, NULL, NULL, NULL, 4, 0, 0);

/* CAN bus-off recovery: poll each controller outside callbacks and ask Zephyr to recover.
 * The MCP2515 driver/version must support can_get_state/can_recover for this to work. */
static void can_recovery_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (true) {
        const struct device *devs[2] = {can_a, can_b};
        for (unsigned bus=0; bus<2; ++bus) {
            enum can_state state;
            struct can_bus_err_cnt counters;
            if (can_get_state(devs[bus], &state, &counters) == 0 && state == CAN_STATE_BUS_OFF) {
                /* Timeout is bounded so a disconnected bus cannot block supervision indefinitely. */
                (void)can_recover(devs[bus], K_MSEC(10));
            }
        }
        k_msleep(10);
    }
}
K_THREAD_DEFINE(can_recovery_tid, 1024, can_recovery_thread, NULL, NULL, NULL, 3, 0, 0);

/* GPIO ISR only wakes this thread. Debounce/state changes/transmission occur in thread context. */
static void test_button_isr(const struct device *port, struct gpio_callback *cb, gpio_port_pins_t pins) {
    ARG_UNUSED(port); ARG_UNUSED(cb); ARG_UNUSED(pins);
    k_sem_give(&test_button_event);
}
/* TEST_BTN: 2 ms debounce; single press enters error, double press clears manual latch. */
static void button_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (true) {
        k_sem_take(&test_button_event, K_FOREVER);
        k_msleep(DEBOUNCE_MS);
        int raw_value = gpio_pin_get_dt(&test_button);
        bool raw = raw_value > 0;
        if (raw == button_stable) continue; /* bounce or coalesced edge */
        button_stable = raw;
        if (!raw) continue; /* only process press edge, not release */
        uint32_t task_start = lab3_timing_start();
        uint32_t now = k_uptime_get_32();
        if (last_press_ms && (uint32_t)(now-last_press_ms) <= DOUBLE_PRESS_MS) {
            k_mutex_lock(&state_lock, K_FOREVER); s.manual_error = false; k_mutex_unlock(&state_lock);
            struct can_frame clear; lab3_pack_fault(&clear, next_seq(ID_FAULT), MY_ZONE, 0); send_both(&clear);
            last_press_ms = 0;
        } else {
            k_mutex_lock(&state_lock, K_FOREVER); s.manual_error = true; s.error = true; k_mutex_unlock(&state_lock);
            send_fault(1); /* reason 1: local test button */
            last_press_ms = now;
        }
        lab3_timing_end(T_TEST_BTN, task_start);
    }
}
K_THREAD_DEFINE(test_btn_tid, 1024, button_thread, NULL, NULL, NULL, 3, 0, 0);

/* PID: 10 ms demo periodic task on N3. It exercises timing without commanding motors. */
#if defined(CONFIG_LAB3_ZONE_N3)
static void pid_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    int32_t demo_integrator = 0;
    int64_t next_release_ms = k_uptime_get();
    while (true) {
        uint32_t task_start = lab3_timing_start();
        lab3_trace_set(10, 1);
        k_mutex_lock(&state_lock, K_FOREVER); int32_t target = s.error ? 0 : s.throttle; k_mutex_unlock(&state_lock);
        demo_integrator += target - demo_integrator; /* placeholder computation, no actuator output */
        ARG_UNUSED(demo_integrator);
        lab3_trace_set(10, 0);
        lab3_timing_end(T_PID, task_start);
        periodic_wait(&next_release_ms, 10);
    }
}
K_THREAD_DEFINE(pid_tid, 1024, pid_thread, NULL, NULL, NULL, 3, 0, 0);
#endif

/* Periodic low-priority console: prints state without logging in the CAN callback/critical path. */
static void diagnostics_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (true) {
        k_mutex_lock(&state_lock, K_FOREVER);
        uint32_t rx=s.rx_count, dup=s.duplicate_count, bad=s.bad_crc_count, rel=s.relay_count;
        int16_t steer=s.steer; uint8_t thr=s.throttle, brk=s.brake, mode=s.blink_mode, phase=s.blink_phase;
        bool err=s.error || s.manual_error; uint32_t age=s.have_ctrl ? k_uptime_get_32()-s.last_ctrl_ms : UINT32_MAX;
        k_mutex_unlock(&state_lock);
        printk("%s state=%s steer=%d throttle=%u%% brake=%u%% blink=%u phase=%u ctrl_age_ms=%u rx=%u dup=%u bad_crc=%u relay=%u q_overflow=%d\n",
               APP_NAME, err?"ERROR":"OK", steer, thr, brk, mode, phase, age, rx, dup, bad, rel, (int)atomic_get(&rx_overflow));
        printk("OBS_MAX_US uptime_ms=%u rx_dispatch=%u can_tx=%u steer_drive=%u hb_mon=%u hb_tx=%u pid=%u test_btn=%u relay=%u counts=%u,%u,%u,%u,%u,%u,%u,%u\n",
               k_uptime_get_32(), lab3_timing_max_us(T_RX_DISPATCH), lab3_timing_max_us(T_CAN_TX), lab3_timing_max_us(T_STEER_DRIVE),
               lab3_timing_max_us(T_HB_MON), lab3_timing_max_us(T_HB_TX), lab3_timing_max_us(T_PID),
               lab3_timing_max_us(T_TEST_BTN), lab3_timing_max_us(T_RELAY), lab3_timing_count(T_RX_DISPATCH), lab3_timing_count(T_CAN_TX),
               lab3_timing_count(T_STEER_DRIVE), lab3_timing_count(T_HB_MON), lab3_timing_count(T_HB_TX),
               lab3_timing_count(T_PID), lab3_timing_count(T_TEST_BTN), lab3_timing_count(T_RELAY));
        k_msleep(250);
    }
}
K_THREAD_DEFINE(diag_tid, 1536, diagnostics_thread, NULL, NULL, NULL, 7, 0, 0);

static void apply_blink_outputs(void) {
    static uint32_t next_error_phase;
    static uint8_t error_phase;
    uint32_t now=k_uptime_get_32();
    k_mutex_lock(&state_lock, K_FOREVER);
    bool err=s.error || s.manual_error; uint8_t mode=s.blink_mode, phase=s.blink_phase;
    k_mutex_unlock(&state_lock);
    if (err) {
        if (now >= next_error_phase) { error_phase ^= 1; next_error_phase=now+250; }
        mode=BLINK_HAZARD; phase=error_phase;
    }
#if defined(CONFIG_LAB3_ZONE_N2)
    lab3_trace_set(11, phase && (mode==BLINK_LEFT || mode==BLINK_HAZARD));
    lab3_trace_set(12, phase && (mode==BLINK_RIGHT || mode==BLINK_HAZARD));
#else
    lab3_trace_set(13, phase && (mode==BLINK_LEFT || mode==BLINK_HAZARD));
    lab3_trace_set(14, phase && (mode==BLINK_RIGHT || mode==BLINK_HAZARD));
#endif
}

static int setup_can(const struct device *dev, unsigned bus) {
    if (!device_is_ready(dev)) { printk("CAN bus %u device not ready\n", bus); return -ENODEV; }
    int rc = can_start(dev);
    if (rc && rc != -EALREADY) { printk("can_start bus %u failed: %d\n", bus, rc); return rc; }
    for (unsigned i=0; i<ARRAY_SIZE(catalog_ids); ++i) {
        struct can_filter filter = {.id=catalog_ids[i], .mask=CAN_STD_ID_MASK, .flags=0};
        filter_ids[bus][i] = can_add_rx_filter(dev, can_rx_callback, (void *)(uintptr_t)bus, &filter);
        if (filter_ids[bus][i] < 0) { printk("CAN RX filter failed bus=%u id=0x%03x rc=%d\n", bus, catalog_ids[i], filter_ids[bus][i]); return filter_ids[bus][i]; }
    }
    return 0;
}

int main(void) {
    int rc=lab3_trace_init(); if (rc) { printk("GPIO test-point setup failed: %d\n", rc); return rc; }
    if (!gpio_is_ready_dt(&test_button) || gpio_pin_configure_dt(&test_button, GPIO_INPUT) != 0) {
        printk("Test button GPIO setup failed; check overlay/wiring\n"); return -ENODEV;
    }
    button_stable = gpio_pin_get_dt(&test_button) > 0;
    gpio_init_callback(&test_button_callback, test_button_isr, BIT(test_button.pin));
    rc = gpio_add_callback(test_button.port, &test_button_callback);
    if (rc != 0) { printk("Test button callback setup failed: %d\n", rc); return rc; }
    rc = gpio_pin_interrupt_configure_dt(&test_button, GPIO_INT_EDGE_BOTH);
    if (rc != 0) { printk("Test button IRQ setup failed: %d\n", rc); return rc; }
    rc=setup_can(can_a,0); if (rc) return rc;
    rc=setup_can(can_b,1); if (rc) return rc;
    if (!device_is_ready(watchdog_dev)) { printk("IWDG device not ready; check &iwdg overlay and WDT driver.\n"); return -ENODEV; }
    struct wdt_timeout_cfg wdt_cfg = { .window = { .min = 0, .max = 1000 }, .callback = NULL, .flags = WDT_FLAG_RESET_SOC };
    watchdog_channel = wdt_install_timeout(watchdog_dev, &wdt_cfg);
    if (watchdog_channel < 0) { printk("IWDG timeout install failed: %d\n", watchdog_channel); return watchdog_channel; }
    rc = wdt_setup(watchdog_dev, 0);
    if (rc != 0) { printk("IWDG setup failed: %d\n", rc); return rc; }
    printk("%s Lab 3 demo online. CAN A/B at 500 kbit/s; outputs are GPIO/LED only.\n", APP_NAME);
    printk("Trace: RX_A=PC2 RX_B=PC3 TX_A=PA0 TX_B=PA1 DEG_A=PB0 DEG_B=PB1 ERR=PC0.\n");
    while (true) { apply_blink_outputs(); k_msleep(2); }
}
