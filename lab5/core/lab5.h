#ifndef TEAM4_LAB5_H
#define TEAM4_LAB5_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define L5_NODES 3
#define L5_CAPACITY 30000
#define L5_RPC_SIZE 24
#define L5_TERM_MAX 65534
enum l5_role { L5_FOLLOWER, L5_CANDIDATE, L5_LEADER };
enum l5_type {
    L5_VOTE = 1,
    L5_VOTE_REPLY,
    L5_APPEND,
    L5_APPEND_REPLY,
    L5_CLIENT,
    L5_REDIRECT,
    L5_REPORT,
    L5_REF_ACK,
    L5_PREVOTE,
    L5_PREVOTE_REPLY
};
/* Compact events encode every event specified in handout Part 3. Index is
 * implicit in the ordered store; voting membership always remains {1,2,3}. */
enum {
    L5_NOOP = 0,
    L5_COCKPIT_OK = 1,
    L5_COCKPIT_ERROR = 2,
    L5_USER_EVENT_BASE = 21,
    L5_EVENT_MAX = 23
};
uint8_t l5_node_event(uint8_t node, bool up);
uint8_t l5_link_event(uint8_t node, uint8_t bus, bool up);
const char *l5_event_name(uint8_t event);
struct l5_entry {
    uint16_t term;
    uint8_t event;
};
struct l5_graph {
    uint8_t nodes, links;
    bool cockpit_ok;
};
void l5_apply(struct l5_graph *g, uint8_t event);
/* Return first bus and bridge node (0 for direct); -1 if disconnected. */
int l5_route(const struct l5_graph *g, uint8_t src, uint8_t dst, uint8_t *bridge);
struct l5_config {
    uint16_t heartbeat_ms, append_ms, missed_heartbeats, jitter_ms, capacity;
    uint8_t default_leader;
    uint32_t seed;
    bool debug;
};
struct l5_rpc {
    uint8_t type, src, dst, success;
    uint16_t term, prev_index, prev_term, commit, index, entry_term;
    uint8_t event, flags;
    uint32_t serial;
    uint16_t reserved;
};
void l5_encode(const struct l5_rpc *m, uint8_t out[L5_RPC_SIZE]);
bool l5_decode(struct l5_rpc *m, const uint8_t in[L5_RPC_SIZE]);
uint8_t l5_crc(const uint8_t *data, size_t size);
/* All store calls complete durably BEFORE returning true. A failure stops
 * voting/acking. read(0) is never called. No allocation in the protocol core. */
struct l5_io {
    void *ctx;
    bool (*read)(void *, uint16_t index, struct l5_entry *);
    bool (*append)(void *, struct l5_entry);
    bool (*truncate)(void *, uint16_t retained);
    bool (*hardstate)(void *, uint16_t term, uint8_t vote);
    void (*send)(void *, const struct l5_rpc *);
    void (*applied)(void *, uint16_t index, struct l5_entry, bool replay);
};
struct l5_raft {
    struct l5_config cfg;
    struct l5_io io;
    struct l5_graph graph;
    /* Projection through the durable suffix; never exposed as committed state. */
    struct l5_graph pending_graph;
    uint16_t term, length, commit, applied, next[4], match[4];
    uint8_t id, leader, vote, votes, role, prevotes;
    bool failed, replaying, prevoting;
    uint32_t rng;
    uint16_t replay_until, event_wanted, event_committed[4];
    /* Count the Pi-acknowledged committed EVENT prefix incrementally. */
    uint16_t held_match, held_acked_events;
    uint64_t deadline_ms, next_append_ms, now_ms, last_leader_ms, next_event_ms;
};
bool l5_init(struct l5_raft *, uint8_t id, struct l5_config, struct l5_io, uint16_t persisted_term,
             uint8_t persisted_vote, uint16_t length, uint64_t now_ms);
void l5_tick(struct l5_raft *, uint64_t now_ms);
void l5_receive(struct l5_raft *, const struct l5_rpc *, uint64_t now_ms);
/* REF is an election heartbeat, NOT a log replication acknowledgement. */
bool l5_heartbeat(struct l5_raft *, uint8_t leader, uint16_t term, uint64_t now_ms);
bool l5_propose(struct l5_raft *, uint8_t event);
/* Idempotent state request including uncommitted suffix, redirected to leader. */
bool l5_request(struct l5_raft *, uint8_t event);
bool l5_user_event(struct l5_raft *);
uint16_t l5_held_events(struct l5_raft *);
/* Client API: proposals redirect as needed; getNetwork exposes committed state. */
bool l5_addNode(struct l5_raft *, uint8_t node);
bool l5_dropNode(struct l5_raft *, uint8_t node);
bool l5_addLink(struct l5_raft *, uint8_t node, uint8_t bus);
bool l5_dropLink(struct l5_raft *, uint8_t node, uint8_t bus);
struct l5_graph l5_getNetwork(const struct l5_raft *);

struct l5_clock {
    uint64_t local_anchor, global_anchor, last_local, last_master, last_return;
    uint64_t epoch_hint;
    double rate;
    int64_t last_error;
    uint16_t term;
    uint8_t leader;
    bool synced, have_pair, have_epoch;
    uint32_t samples, rejected;
};
void l5_clock_init(struct l5_clock *, uint64_t raw_us);
uint64_t l5_global(struct l5_clock *, uint64_t raw_us);
bool l5_clock_ref(struct l5_clock *, uint8_t leader, uint16_t term, uint32_t master_low_us,
                  uint64_t receive_raw_us, uint32_t delay_us);
void l5_clock_lead(struct l5_clock *, uint8_t id, uint16_t term, uint64_t raw_us);
#endif
