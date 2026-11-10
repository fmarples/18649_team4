#include "lab5_runtime.h"
#include "agent.h"
#include "lab5.h"
#include "lab5_config.h"
#include "store.h"
#include <string.h>
#include <time.h>
#include <zephyr/drivers/flash.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include <zephyr/storage/flash_map.h>

static struct l5_raft raft;
static struct l5_store store;
static struct l5_clock net_clock;
static struct l5_wire wire;
static struct l5_agent agent;
static const struct flash_area *area;
static void (*send_frame)(unsigned, const struct can_frame *);
K_MUTEX_DEFINE(raft_lock);
K_SEM_DEFINE(ready, 0, 1);
K_MSGQ_DEFINE(applied_queue, 8, 128, 4);
struct pps_row {
    uint64_t global, raw;
    int64_t rate_ppb, correction;
    uint8_t node;
};
K_MSGQ_DEFINE(pps_queue, sizeof(struct pps_row), 4, 8);
struct debug_row {
    uint16_t term, index, commit;
    uint8_t type, src, dst, role, leader, failed;
};
K_MSGQ_DEFINE(debug_queue, sizeof(struct debug_row), 64, 4);
struct log_row {
    uint16_t index, term;
    uint8_t event, replay, pad[2];
};
static uint32_t log_drops;
static const struct gpio_dt_spec pps = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), pps_gpios);
static const struct gpio_dt_spec leader_pin = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), leader_gpios);
static const struct gpio_dt_spec sync_pin = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), sync_gpios);
static const struct gpio_dt_spec ref_pin = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), ref_rx_gpios);
uint64_t lab5_raw_us(void) { return k_cyc_to_us_floor64(k_cycle_get_64()); }
static bool flash_read_cb(void *ctx, uint32_t off, void *p, size_t n) {
    ARG_UNUSED(ctx);
    return flash_area_read(area, off, p, n) == 0;
}
static bool flash_write_cb(void *ctx, uint32_t off, const void *p, size_t n) {
    ARG_UNUSED(ctx);
    return flash_area_write(area, off, p, n) == 0;
}
static bool flash_erase_cb(void *ctx, unsigned bank) {
    ARG_UNUSED(ctx);
    return flash_area_erase(area, bank * L5_BANK_SIZE, L5_BANK_SIZE) == 0;
}
static bool read_entry(void *ctx, uint16_t i, struct l5_entry *e) {
    ARG_UNUSED(ctx);
    return l5_store_read(&store, i, e);
}
static bool append_entry(void *ctx, struct l5_entry e) {
    ARG_UNUSED(ctx);
    return l5_store_append(&store, e);
}
static bool truncate_entries(void *ctx, uint16_t i) {
    ARG_UNUSED(ctx);
    return l5_store_truncate(&store, i);
}
static bool hard_state(void *ctx, uint16_t t, uint8_t v) {
    ARG_UNUSED(ctx);
    return l5_store_hardstate(&store, t, v);
}
static void send_packet(void *ctx, unsigned bus, const struct l5_packet *p) {
    ARG_UNUSED(ctx);
    struct can_frame f = {.id = p->id, .dlc = 8};
    memcpy(f.data, p->data, 8);
    if (p->id == 0x80U + raft.id) {
        /* A durable operation in this tick may have delayed REF creation.
         * Stamp our own reference at enqueue time; preserve relayed origins. */
        uint32_t stamp = (uint32_t)l5_global(&net_clock, lab5_raw_us());
        for (unsigned i = 0; i < 4; i++)
            f.data[3 + i] = (uint8_t)(stamp >> (8 * i));
        f.data[7] = l5_crc(f.data, 7);
    }
    if (send_frame)
        send_frame(bus, &f);
}
static void send_rpc(void *ctx, const struct l5_rpc *m) {
    ARG_UNUSED(ctx);
    l5_agent_rpc(&agent, m);
    if (L5_CFG_DEBUG) {
        struct debug_row row = {m->term, m->index,  m->commit,   m->type,    m->src,
                                m->dst,  raft.role, raft.leader, raft.failed};
        if (k_msgq_put(&debug_queue, &row, K_NO_WAIT))
            log_drops++;
    }
}
static void on_apply(void *ctx, uint16_t i, struct l5_entry e, bool replay) {
    ARG_UNUSED(ctx);
    struct log_row row = {.index = i, .term = e.term, .event = e.event, .replay = replay};
    if (k_msgq_put(&applied_queue, &row, K_NO_WAIT))
        log_drops++;
}
int lab5_runtime_init(unsigned id, void (*send)(unsigned, const struct can_frame *)) {
    send_frame = send;
    int rc = flash_area_open(FIXED_PARTITION_ID(lab5_storage), &area);
    if (rc)
        return rc;
    if (area->fa_size != L5_STORE_SIZE)
        return -EINVAL;
    struct l5_flash_io flash = {NULL, flash_read_cb, flash_write_cb, flash_erase_cb};
    if (!l5_store_open(&store, flash))
        return -EIO;
    /* A reset during runtime compaction leaves the old, full journal valid.
     * Reclaim it before the 1 s watchdog starts, keeping every entry/vote.
     * This does not establish runtime erase latency; that remains a bench gate. */
    uint32_t generation = store.generation;
    if (!l5_store_prepare_boot(&store))
        return -EIO;
    if (store.generation != generation)
        printk("STORE boot_compaction preserved term=%u vote=%u entries=%u\n",
               store.term, store.vote, store.length);
    const struct gpio_dt_spec *pins[] = {&pps, &leader_pin, &sync_pin, &ref_pin};
    for (unsigned i = 0; i < ARRAY_SIZE(pins); i++) {
        if (!gpio_is_ready_dt(pins[i]))
            return -ENODEV;
        rc = gpio_pin_configure_dt(pins[i], GPIO_OUTPUT_INACTIVE);
        if (rc)
            return rc;
    }
    l5_clock_init(&net_clock, lab5_raw_us());
    l5_agent_init(&agent, &raft, &net_clock, &wire, NULL, send_packet, L5_CFG_CAN_DELAY_US);
    struct l5_config cfg = {L5_CFG_HEARTBEAT_MS, L5_CFG_APPEND_MS, L5_CFG_MISSED_HEARTBEATS,
                            L5_CFG_JITTER_MS,    L5_CFG_CAPACITY,  L5_CFG_DEFAULT_LEADER,
                            L5_CFG_SEED,         L5_CFG_DEBUG};
    struct l5_io io = {NULL,       read_entry, append_entry, truncate_entries,
                       hard_state, send_rpc,   on_apply};
    return l5_init(&raft, id, cfg, io, store.term, store.vote, store.length, lab5_raw_us() / 1000)
               ? 0
               : -EIO;
}
void lab5_ready(void) { k_sem_give(&ready); }
void lab5_pause(bool paused) {
    k_mutex_lock(&raft_lock, K_FOREVER);
    agent.paused = paused;
    k_mutex_unlock(&raft_lock);
}
bool lab5_runtime_receive(unsigned bus, const struct can_frame *f, uint64_t raw) {
    if (f->flags & (CAN_FRAME_IDE | CAN_FRAME_RTR) || f->dlc != 8)
        return false;
    struct l5_packet p = {.id = (uint16_t)f->id};
    memcpy(p.data, f->data, 8);
    k_mutex_lock(&raft_lock, K_FOREVER);
    uint32_t samples = net_clock.samples;
    uint64_t processed = lab5_raw_us();
    uint32_t delay = agent.delay_us;
    agent.delay_us += (uint32_t)(processed - raw);
    bool used = l5_agent_receive(&agent, bus, &p, processed);
    agent.delay_us = delay;
    if (net_clock.samples != samples) {
        gpio_pin_toggle_dt(&ref_pin);
        uint64_t global = l5_global(&net_clock, lab5_raw_us());
        struct timespec t = {.tv_sec = (time_t)(global / 1000000),
                             .tv_nsec = (long)(global % 1000000) * 1000};
        (void)clock_settime(CLOCK_REALTIME, &t); /* uptime/cycle clock is unchanged */
    }
    k_mutex_unlock(&raft_lock);
    return used;
}
uint64_t lab5_global_us(void) {
    k_mutex_lock(&raft_lock, K_FOREVER);
    uint64_t t = l5_global(&net_clock, lab5_raw_us());
    k_mutex_unlock(&raft_lock);
    return t;
}
bool lab5_error(void) {
    k_mutex_lock(&raft_lock, K_FOREVER);
    bool e = l5_agent_error(&agent, lab5_raw_us());
    k_mutex_unlock(&raft_lock);
    return e;
}
unsigned lab5_hazard_hz(void) {
    k_mutex_lock(&raft_lock, K_FOREVER);
    unsigned hz = l5_agent_hazard_hz(&agent, lab5_raw_us());
    k_mutex_unlock(&raft_lock);
    return hz;
}
static void protocol_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);
    k_sem_take(&ready, K_FOREVER);
    uint64_t last_second = 0, pulse_end = 0;
    uint16_t previous_term = 0;
    uint8_t previous_role = 255;
    while (true) {
        k_mutex_lock(&raft_lock, K_FOREVER);
        /* Reception can move the clock anchor while this task waits. Read raw
         * only after acquiring ownership, then refresh after durable writes. */
        uint64_t raw = lab5_raw_us();
        agent.upstream_ok = true;
        l5_agent_tick(&agent, raw);
        raw = lab5_raw_us();
        uint64_t global = l5_global(&net_clock, raw);
        gpio_pin_set_dt(&leader_pin, raft.role == L5_LEADER && !agent.paused && !raft.failed);
        gpio_pin_set_dt(&sync_pin, l5_agent_synced(&agent, raw));
        if (global / 1000000 != last_second) {
            last_second = global / 1000000;
            pulse_end = raw + 1000;
            gpio_pin_set_dt(&pps, 1);
            struct pps_row row = {
                global, raw, (int64_t)((net_clock.rate - 1.0) * 1e9),
                (int64_t)((raw - net_clock.local_anchor) * (net_clock.rate - 1.0)), raft.id};
            if (k_msgq_put(&pps_queue, &row, K_NO_WAIT))
                log_drops++;
        }
        if (raw >= pulse_end)
            gpio_pin_set_dt(&pps, 0);
        if (raft.term != previous_term || raft.role != previous_role) {
            struct debug_row row = {raft.term, raft.length, raft.commit, 0,          raft.id,
                                    0,         raft.role,   raft.leader, raft.failed};
            if (k_msgq_put(&debug_queue, &row, K_NO_WAIT))
                log_drops++;
            previous_term = raft.term;
            previous_role = raft.role;
        }
        k_mutex_unlock(&raft_lock);
        k_sleep(K_USEC(200));
    }
}
K_THREAD_DEFINE(protocol_tid, 3072, protocol_thread, NULL, NULL, NULL, 2, 0, 0);
static void log_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);
    struct log_row row;
    while (true) {
        if (!k_msgq_get(&applied_queue, &row, K_MSEC(10)))
            printk("COMMIT index=%u term=%u event=%s replayed=%u\n", row.index, row.term,
                   l5_event_name(row.event), row.replay);
        struct pps_row p;
        while (!k_msgq_get(&pps_queue, &p, K_NO_WAIT))
            printk("PPS node=%u global_us=%llu local_us=%llu rate_ppb=%lld correction_us=%lld\n",
                   p.node, (unsigned long long)p.global, (unsigned long long)p.raw,
                   (long long)p.rate_ppb, (long long)p.correction);
        struct debug_row d;
        /* A debug burst must not postpone committed entries indefinitely. */
        for (unsigned i = 0; i < 8 && !k_msgq_get(&debug_queue, &d, K_NO_WAIT); i++)
            printk("RAFT type=%u src=%u dst=%u term=%u index=%u commit=%u role=%u leader=%u "
                   "failed=%u log_drops=%u\n",
                   d.type, d.src, d.dst, d.term, d.index, d.commit, d.role, d.leader, d.failed,
                   log_drops);
    }
}
K_THREAD_DEFINE(log_tid, 1024, log_thread, NULL, NULL, NULL, 11, 0, 0);
static int network_cmd(const struct shell *sh, size_t argc, char **argv) {
    ARG_UNUSED(argc);
    ARG_UNUSED(argv);
    k_mutex_lock(&raft_lock, K_FOREVER);
    shell_print(sh,
                "NETWORK node=%u term=%u leader=%u commit=%u nodes=0x%x links=0x%x cockpit_ok=%u",
                raft.id, raft.term, raft.leader, raft.commit, raft.graph.nodes, raft.graph.links,
                raft.graph.cockpit_ok);
    k_mutex_unlock(&raft_lock);
    return 0;
}
static int log_cmd(const struct shell *sh, size_t argc, char **argv) {
    ARG_UNUSED(argc);
    ARG_UNUSED(argv);
    k_mutex_lock(&raft_lock, K_FOREVER);
    for (uint16_t i = 1; i <= raft.commit; i++) {
        struct l5_entry e;
        if (l5_store_read(&store, i, &e))
            shell_print(sh, "LOG index=%u term=%u event=%s", i, e.term, l5_event_name(e.event));
    }
    k_mutex_unlock(&raft_lock);
    return 0;
}
static int event_cmd(const struct shell *sh, size_t argc, char **argv) {
    ARG_UNUSED(argc);
    ARG_UNUSED(argv);
    k_mutex_lock(&raft_lock, K_FOREVER);
    bool queued = l5_user_event(&raft);
    k_mutex_unlock(&raft_lock);
    shell_print(sh, "EVENT %s",
                queued ? "queued; wait for COMMIT"
                       : "not queued: no leader, catching up, or storage full");
    return queued ? 0 : -EAGAIN;
}
SHELL_STATIC_SUBCMD_SET_CREATE(
    lab5_sub, SHELL_CMD(network, NULL, "Committed getNetwork snapshot", network_cmd),
    SHELL_CMD(log, NULL, "Dump committed log (use while idle)", log_cmd),
    SHELL_CMD(event, NULL, "Queue one replicated EVENT from this node", event_cmd),
    SHELL_SUBCMD_SET_END);
SHELL_CMD_REGISTER(lab5, &lab5_sub, "Lab 5 consensus diagnostics", NULL);
