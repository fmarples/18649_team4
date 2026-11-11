#ifndef LAB5_AGENT_H
#define LAB5_AGENT_H
#include "wire.h"
#define L5_HELLO_BASE 0x110U
struct l5_seen_packet {
    uint16_t id;
    uint8_t data[8];
    uint64_t ms;
    bool used;
};
struct l5_agent {
    struct l5_raft *raft;
    struct l5_clock *clock;
    struct l5_wire *wire;
    void *ctx;
    void (*send_packet)(void *, unsigned bus, const struct l5_packet *);
    uint64_t direct[4][2], reports[4], next_periodic, last_ref;
    uint8_t masks[4][2], upstream[4], hello_seq, ref_seq, rx_ref_seq, rx_ref_src;
    uint16_t rx_ref_term, clock_term;
    uint16_t held_events;
    uint8_t clock_leader;
    bool direct_seen[4][2], report_seen[4], upstream_ok, paused, ref_seen;
    struct l5_seen_packet seen[128];
    unsigned seen_next;
    uint32_t delay_us, relay_count, report_count;
};
void l5_agent_init(struct l5_agent *, struct l5_raft *, struct l5_clock *, struct l5_wire *, void *,
                   void (*)(void *, unsigned, const struct l5_packet *), uint32_t delay_us);
void l5_agent_rpc(struct l5_agent *, const struct l5_rpc *);
void l5_agent_tick(struct l5_agent *, uint64_t raw_us);
/* Handles protocol packets and forwards both Lab 3 and Lab 5 traffic. Returns
 * true for Lab 5 packets; false lets the application process a Lab 3 packet. */
bool l5_agent_receive(struct l5_agent *, unsigned bus, const struct l5_packet *, uint64_t raw_us);
bool l5_agent_error(const struct l5_agent *, uint64_t raw_us);
enum l5_health_reason {
    L5_HEALTH_PAUSED = 1, L5_HEALTH_STORAGE = 2, L5_HEALTH_ISOLATED = 4,
    L5_HEALTH_PI_STALE = 8, L5_HEALTH_INPUT = 16
};
unsigned l5_agent_error_reason(const struct l5_agent *, uint64_t raw_us);
uint32_t l5_agent_report_age(const struct l5_agent *, unsigned node, uint64_t raw_us);
unsigned l5_agent_hazard_hz(const struct l5_agent *, uint64_t raw_us);
bool l5_agent_synced(const struct l5_agent *, uint64_t raw_us);
#endif
