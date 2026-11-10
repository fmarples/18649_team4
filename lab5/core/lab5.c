#include "lab5.h"
#include <string.h>

uint8_t l5_node_event(uint8_t n, bool up) { return n >= 1 && n <= 3 ? 3 + (n - 1) * 2 + !up : 255; }
uint8_t l5_link_event(uint8_t n, uint8_t b, bool up) {
    return n >= 1 && n <= 3 && b < 2 ? 9 + ((n - 1) * 2 + b) * 2 + !up : 255;
}
const char *l5_event_name(uint8_t e) {
    static const char *const names[] = {"NOOP",
                                        "COCKPIT_OK",
                                        "COCKPIT_ERROR",
                                        "NODE_1_UP",
                                        "NODE_1_DOWN",
                                        "NODE_2_UP",
                                        "NODE_2_DOWN",
                                        "NODE_3_UP",
                                        "NODE_3_DOWN",
                                        "CANLINK_1_A_UP",
                                        "CANLINK_1_A_DOWN",
                                        "CANLINK_1_B_UP",
                                        "CANLINK_1_B_DOWN",
                                        "CANLINK_2_A_UP",
                                        "CANLINK_2_A_DOWN",
                                        "CANLINK_2_B_UP",
                                        "CANLINK_2_B_DOWN",
                                        "CANLINK_3_A_UP",
                                        "CANLINK_3_A_DOWN",
                                        "CANLINK_3_B_UP",
                                        "CANLINK_3_B_DOWN",
                                        "EVENT_N1",
                                        "EVENT_N2",
                                        "EVENT_N3"};
    return e <= L5_EVENT_MAX ? names[e] : "INVALID";
}
void l5_apply(struct l5_graph *g, uint8_t e) {
    if (e == L5_COCKPIT_OK)
        g->cockpit_ok = true;
    else if (e == L5_COCKPIT_ERROR)
        g->cockpit_ok = false;
    else if (e >= 3 && e <= 8) {
        unsigned n = (e - 3) / 2;
        uint8_t bit = 1U << n;
        if ((e - 3) % 2 == 0)
            g->nodes |= bit;
        else {
            g->nodes &= (uint8_t)~bit;
            g->links &= (uint8_t)~(3U << (2 * n));
        }
    } else if (e >= 9 && e <= 20) {
        unsigned link = (e - 9) / 2;
        uint8_t bit = 1U << link;
        if ((e - 9) % 2 == 0 && (g->nodes & (1U << (link / 2))))
            g->links |= bit;
        else if ((e - 9) % 2)
            g->links &= (uint8_t)~bit;
    }
}
int l5_route(const struct l5_graph *g, uint8_t src, uint8_t dst, uint8_t *bridge) {
    if (src < 1 || src > 3 || dst < 1 || dst > 3)
        return -1;
    if (!(g->nodes & (1U << (src - 1))) || !(g->nodes & (1U << (dst - 1))))
        return -1;
    uint8_t a = (g->links >> (2 * (src - 1))) & 3, b = (g->links >> (2 * (dst - 1))) & 3;
    *bridge = 0;
    if (a & b)
        return (a & b & 1) ? 0 : 1;
    for (uint8_t n = 1; n <= 3; n++)
        if (n != src && n != dst && (g->nodes & (1U << (n - 1))) &&
            ((g->links >> (2 * (n - 1))) & 3) == 3 && a && b) {
            *bridge = n;
            return (a & 1) ? 0 : 1;
        }
    return -1;
}
uint8_t l5_crc(const uint8_t *p, size_t n) {
    uint8_t c = 0;
    while (n--) {
        c ^= *p++;
        for (unsigned i = 0; i < 8; i++)
            c = (c & 128) ? (uint8_t)((c << 1) ^ 7) : (uint8_t)(c << 1);
    }
    return c;
}
static void put16(uint8_t *p, uint16_t x) {
    p[0] = (uint8_t)x;
    p[1] = (uint8_t)(x >> 8);
}
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
void l5_encode(const struct l5_rpc *m, uint8_t p[L5_RPC_SIZE]) {
    memset(p, 0, L5_RPC_SIZE);
    p[0] = 1;
    p[1] = m->type;
    p[2] = m->src;
    p[3] = m->dst;
    put16(p + 4, m->term);
    put16(p + 6, m->prev_index);
    put16(p + 8, m->prev_term);
    put16(p + 10, m->commit);
    put16(p + 12, m->index);
    put16(p + 14, m->entry_term);
    p[16] = m->event;
    p[17] = m->success;
    p[18] = m->flags;
    for (unsigned i = 0; i < 4; i++)
        p[19 + i] = (uint8_t)(m->serial >> (8 * i));
    p[23] = l5_crc(p, 23);
}
bool l5_decode(struct l5_rpc *m, const uint8_t p[L5_RPC_SIZE]) {
    if (p[0] != 1 || p[1] < L5_VOTE || p[1] > L5_PREVOTE_REPLY || p[2] < 1 || p[2] > 3 ||
        p[3] > 3 || p[23] != l5_crc(p, 23))
        return false;
    memset(m, 0, sizeof(*m));
    m->type = p[1];
    m->src = p[2];
    m->dst = p[3];
    m->term = get16(p + 4);
    m->prev_index = get16(p + 6);
    m->prev_term = get16(p + 8);
    m->commit = get16(p + 10);
    m->index = get16(p + 12);
    m->entry_term = get16(p + 14);
    m->event = p[16];
    m->success = p[17];
    m->flags = p[18];
    for (unsigned i = 0; i < 4; i++)
        m->serial |= (uint32_t)p[19 + i] << (8 * i);
    return m->term <= L5_TERM_MAX && m->event <= L5_EVENT_MAX && m->success <= 1;
}
static uint32_t random32(struct l5_raft *r) {
    uint32_t x = r->rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return r->rng = x;
}
static void deadline(struct l5_raft *r) {
    r->deadline_ms = r->now_ms + r->cfg.heartbeat_ms * r->cfg.missed_heartbeats +
                     random32(r) % (r->cfg.jitter_ms + 1U);
}
static uint16_t term_at(struct l5_raft *r, uint16_t i) {
    if (!i)
        return 0;
    struct l5_entry e;
    if (i > r->length || !r->io.read(r->io.ctx, i, &e)) {
        r->failed = true;
        return 0;
    }
    return e.term;
}
static bool hard(struct l5_raft *r, uint16_t t, uint8_t v) {
    if (t > L5_TERM_MAX || !r->io.hardstate(r->io.ctx, t, v)) {
        r->failed = true;
        return false;
    }
    r->term = t;
    r->vote = v;
    return true;
}
static bool follower(struct l5_raft *r, uint16_t term, uint8_t leader) {
    if (leader &&
        (r->role != L5_FOLLOWER || r->leader != leader ||
         r->now_ms - r->last_leader_ms >= r->cfg.heartbeat_ms * r->cfg.missed_heartbeats)) {
        r->replaying = true;
        r->replay_until = r->applied;
    }
    if (term > r->term && !hard(r, term, 0))
        return false;
    r->role = L5_FOLLOWER;
    r->leader = leader;
    r->votes = 0;
    r->prevoting = false;
    if (leader)
        r->last_leader_ms = r->now_ms;
    deadline(r);
    return true;
}
static void send(struct l5_raft *r, struct l5_rpc m) {
    m.src = r->id;
    m.term = r->term;
    if (!r->failed)
        r->io.send(r->io.ctx, &m);
}
static void apply(struct l5_raft *r) {
    while (r->applied < r->commit && !r->failed) {
        struct l5_entry e;
        if (!r->io.read(r->io.ctx, r->applied + 1, &e)) {
            r->failed = true;
            break;
        }
        ++r->applied;
        l5_apply(&r->graph, e.event);
        if (e.event >= L5_USER_EVENT_BASE)
            r->event_committed[e.event - L5_USER_EVENT_BASE + 1]++;
        if (r->io.applied)
            r->io.applied(r->io.ctx, r->applied, e, r->replaying);
    }
    if (r->applied >= r->replay_until)
        r->replaying = false;
}
static void append_to(struct l5_raft *r, uint8_t peer) {
    uint16_t next = r->next[peer];
    struct l5_rpc m = {
        .type = L5_APPEND, .dst = peer, .prev_index = (uint16_t)(next - 1), .commit = r->commit};
    m.prev_term = term_at(r, m.prev_index);
    if (next <= r->length) {
        struct l5_entry e;
        if (!r->io.read(r->io.ctx, next, &e)) {
            r->failed = true;
            return;
        }
        m.index = next;
        m.entry_term = e.term;
        m.event = e.event;
        m.flags = 1;
    }
    send(r, m);
}
static void broadcast_append(struct l5_raft *r) {
    for (uint8_t n = 1; n <= 3; n++)
        if (n != r->id)
            append_to(r, n);
}
static void become_leader(struct l5_raft *r) {
    r->role = L5_LEADER;
    r->leader = r->id;
    for (unsigned n = 1; n <= 3; n++) {
        r->next[n] = r->length + 1;
        r->match[n] = 0;
    }
    r->match[r->id] = r->length;
    r->next_append_ms = r->now_ms + r->cfg.append_ms;
    /* Current-term barrier commits any preceding entries from older leaders. */
    (void)l5_propose(r, L5_NOOP);
}
static bool rebuild_pending_graph(struct l5_raft *r) {
    struct l5_graph pending = {0};
    for (uint16_t i = 1; i <= r->length; i++) {
        struct l5_entry e;
        if (!r->io.read(r->io.ctx, i, &e)) {
            r->failed = true;
            return false;
        }
        l5_apply(&pending, e.event);
    }
    r->pending_graph = pending;
    return true;
}
bool l5_init(struct l5_raft *r, uint8_t id, struct l5_config c, struct l5_io io, uint16_t term,
             uint8_t vote, uint16_t length, uint64_t now) {
    if (id < 1 || id > 3 || !c.heartbeat_ms || !c.append_ms || !c.missed_heartbeats ||
        !c.capacity || c.capacity > L5_CAPACITY || length > c.capacity || term > L5_TERM_MAX ||
        vote > 3 || c.default_leader > 3 || !io.read || !io.append || !io.truncate ||
        !io.hardstate || !io.send)
        return false;
    memset(r, 0, sizeof(*r));
    r->id = id;
    r->cfg = c;
    r->io = io;
    r->term = term;
    r->vote = vote;
    r->length = length;
    r->rng = (c.seed ^ (0x9e3779b9U * id)) | 1;
    r->now_ms = now;
    r->last_leader_ms = now;
    r->replaying = true;
    deadline(r);
    if (!rebuild_pending_graph(r))
        return false;
    /* Default leader is a COLD cluster bootstrap only, never a restart override. */
    if (!term && !length && c.default_leader) {
        if (!hard(r, 1, c.default_leader))
            return false;
        r->leader = c.default_leader;
        if (id == c.default_leader)
            become_leader(r);
    }
    return !r->failed;
}
static uint16_t event_count(struct l5_raft *r, uint8_t node, uint16_t through) {
    uint16_t count = r->event_committed[node];
    for (uint16_t i = r->applied + 1; i <= through; i++) {
        struct l5_entry e;
        if (!r->io.read(r->io.ctx, i, &e)) {
            r->failed = true;
            break;
        }
        if (e.event == L5_USER_EVENT_BASE + node - 1)
            count++;
    }
    return count;
}
static void client_event(struct l5_raft *r, uint8_t src, uint32_t serial) {
    uint16_t count = event_count(r, src, r->length);
    if (serial == (uint32_t)count + 1)
        (void)l5_propose(r, L5_USER_EVENT_BASE + src - 1);
}
uint16_t l5_held_events(struct l5_raft *r) {
    if (r->role != L5_LEADER || r->id == 1)
        return 0;
    uint16_t matched = r->match[1] < r->commit ? r->match[1] : r->commit;
    if (matched < r->held_match) {
        /* A new leadership term starts peer acknowledgement at zero. */
        r->held_match = 0;
        r->held_acked_events = 0;
    }
    for (uint16_t i = r->held_match + 1; i <= matched; i++) {
        struct l5_entry e;
        if (!r->io.read(r->io.ctx, i, &e)) {
            r->failed = true;
            return 0;
        }
        r->held_acked_events += e.event >= L5_USER_EVENT_BASE;
        r->held_match = i;
    }
    /* Applied committed entries are immutable. Do not rescan the full backlog
     * every 20 ms while the Pi is absent; that starves the MCU's lower tasks. */
    return r->event_committed[1] + r->event_committed[2] + r->event_committed[3] -
           r->held_acked_events;
}
bool l5_user_event(struct l5_raft *r) {
    if (r->failed || !r->leader || r->replaying)
        return false;
    uint16_t committed = event_count(r, r->id, r->commit);
    if (r->event_wanted < committed)
        r->event_wanted = committed;
    if (r->event_wanted >= r->cfg.capacity)
        return false;
    r->event_wanted++;
    r->next_event_ms = 0;
    return true;
}
static void begin_election(struct l5_raft *r) {
    if (!hard(r, r->term + 1, r->id))
        return;
    r->prevoting = false;
    r->role = L5_CANDIDATE;
    r->leader = 0;
    r->votes = 1U << r->id;
    deadline(r);
    struct l5_rpc m = {.type = L5_VOTE, .index = r->length, .entry_term = term_at(r, r->length)};
    send(r, m);
}
void l5_tick(struct l5_raft *r, uint64_t now) {
    r->now_ms = now;
    if (r->failed)
        return;
    if (r->event_wanted && now >= r->next_event_ms && r->leader) {
        uint16_t count = event_count(r, r->id, r->commit);
        r->next_event_ms = now + r->cfg.heartbeat_ms;
        if (count < r->event_wanted) {
            if (r->role == L5_LEADER)
                client_event(r, r->id, count + 1);
            else
                send(r, (struct l5_rpc){.type = L5_CLIENT,
                                        .dst = r->leader,
                                        .event = (uint8_t)(L5_USER_EVENT_BASE + r->id - 1),
                                        .serial = count + 1});
        }
    }
    if (r->role == L5_LEADER) {
        if (now >= r->next_append_ms) {
            r->next_append_ms = now + r->cfg.append_ms;
            broadcast_append(r);
        }
        return;
    }
    if (now < r->deadline_ms)
        return;
    /* Pre-vote prevents an isolated follower from inflating durable terms. */
    r->prevoting = true;
    r->prevotes = 1U << r->id;
    deadline(r);
    struct l5_rpc m = {.type = L5_PREVOTE,
                       .src = r->id,
                       .term = (uint16_t)(r->term + 1),
                       .index = r->length,
                       .entry_term = term_at(r, r->length)};
    if (r->term < L5_TERM_MAX)
        r->io.send(r->io.ctx, &m);
    else
        r->failed = true;
}
bool l5_heartbeat(struct l5_raft *r, uint8_t leader, uint16_t term, uint64_t now) {
    r->now_ms = now;
    if (r->failed || leader < 1 || leader > 3 || leader == r->id || term < r->term || !term)
        return false;
    if (term == r->term && r->leader && r->leader != leader)
        return false;
    return follower(r, term, leader);
}
bool l5_propose(struct l5_raft *r, uint8_t e) {
    if (r->failed || r->role != L5_LEADER || e > L5_EVENT_MAX || r->length >= r->cfg.capacity)
        return false;
    struct l5_entry entry = {r->term, e};
    if (!r->io.append(r->io.ctx, entry)) {
        r->failed = true;
        return false;
    }
    ++r->length;
    l5_apply(&r->pending_graph, e);
    r->match[r->id] = r->length;
    broadcast_append(r);
    return true;
}
static bool graph_equal(struct l5_graph a, struct l5_graph b) {
    return a.nodes == b.nodes && a.links == b.links && a.cockpit_ok == b.cockpit_ok;
}
bool l5_request(struct l5_raft *r, uint8_t event) {
    if (event == 0 || event >= L5_USER_EVENT_BASE || r->failed)
        return false;
    if (r->role != L5_LEADER) {
        if (!r->leader)
            return false;
        send(r, (struct l5_rpc){.type = L5_CLIENT, .dst = r->leader, .event = event});
        return true;
    }
    struct l5_graph next = r->pending_graph;
    l5_apply(&next, event);
    return graph_equal(r->pending_graph, next) || l5_propose(r, event);
}
bool l5_addNode(struct l5_raft *r, uint8_t n) { return l5_request(r, l5_node_event(n, true)); }
bool l5_dropNode(struct l5_raft *r, uint8_t n) { return l5_request(r, l5_node_event(n, false)); }
bool l5_addLink(struct l5_raft *r, uint8_t n, uint8_t b) {
    return l5_request(r, l5_link_event(n, b, true));
}
bool l5_dropLink(struct l5_raft *r, uint8_t n, uint8_t b) {
    return l5_request(r, l5_link_event(n, b, false));
}
struct l5_graph l5_getNetwork(const struct l5_raft *r) { return r->graph; }
void l5_receive(struct l5_raft *r, const struct l5_rpc *m, uint64_t now) {
    r->now_ms = now;
    if (r->failed || m->src < 1 || m->src > 3 || m->src == r->id || (m->dst && m->dst != r->id) ||
        m->term > L5_TERM_MAX)
        return;
    if (m->type == L5_PREVOTE) {
        uint16_t last = term_at(r, r->length);
        bool grant = m->term >= r->term + 1 && r->role != L5_LEADER &&
                     now - r->last_leader_ms >= r->cfg.heartbeat_ms * r->cfg.missed_heartbeats &&
                     (m->entry_term > last || (m->entry_term == last && m->index >= r->length));
        struct l5_rpc reply = {.type = L5_PREVOTE_REPLY,
                               .src = r->id,
                               .dst = m->src,
                               .term = m->term,
                               .success = grant};
        if (!r->failed)
            r->io.send(r->io.ctx, &reply);
        return;
    }
    if (m->type == L5_PREVOTE_REPLY) {
        if (r->prevoting && m->term == r->term + 1 && m->success) {
            r->prevotes |= 1U << m->src;
            unsigned count = 0;
            for (unsigned n = 1; n <= 3; n++)
                count += (r->prevotes >> n) & 1U;
            if (count >= 2)
                begin_election(r);
        }
        return;
    }
    if (m->term > r->term && !follower(r, m->term, 0))
        return;
    if (m->type == L5_REDIRECT) {
        if (r->role != L5_LEADER && m->term == r->term && m->flags >= 1 && m->flags <= 3) {
            r->leader = m->flags;
            r->next_event_ms = 0;
        }
        return;
    }
    if (m->type == L5_CLIENT) {
        if (r->role == L5_LEADER) {
            if (m->event == L5_USER_EVENT_BASE + m->src - 1)
                client_event(r, m->src, m->serial);
            else
                (void)l5_request(r, m->event);
        } else
            send(r, (struct l5_rpc){.type = L5_REDIRECT, .dst = m->src, .flags = r->leader});
        return;
    }
    if (m->type == L5_VOTE) {
        uint16_t last = term_at(r, r->length);
        bool fresh = m->entry_term > last || (m->entry_term == last && m->index >= r->length);
        bool grant = m->term == r->term && (!r->vote || r->vote == m->src) && fresh;
        if (grant) {
            if (!hard(r, r->term, m->src))
                return;
            deadline(r);
        }
        send(r, (struct l5_rpc){.type = L5_VOTE_REPLY, .dst = m->src, .success = grant});
        return;
    }
    if (m->type == L5_VOTE_REPLY) {
        if (r->role == L5_CANDIDATE && m->term == r->term && m->success) {
            r->votes |= 1U << m->src;
            unsigned count = 0;
            for (unsigned n = 1; n <= 3; n++)
                count += (r->votes >> n) & 1U;
            if (count >= 2)
                become_leader(r);
        }
        return;
    }
    if (m->type == L5_APPEND) {
        bool ok = false;
        uint16_t matched = m->prev_index;
        if (m->term == r->term && (!r->leader || r->leader == m->src) &&
            follower(r, m->term, m->src) && m->prev_index <= r->length &&
            term_at(r, m->prev_index) == m->prev_term) {
            ok = true;
            if (m->flags & 1) {
                if (m->index != m->prev_index + 1 || m->index > r->cfg.capacity || !m->entry_term ||
                    m->entry_term > m->term || m->event > L5_EVENT_MAX)
                    ok = false;
                else {
                    if (m->index <= r->length) {
                        struct l5_entry e;
                        if (!r->io.read(r->io.ctx, m->index, &e)) {
                            r->failed = true;
                            return;
                        }
                        if (e.term != m->entry_term || e.event != m->event) {
                            if (m->index <= r->commit)
                                ok = false;
                            else if (!r->io.truncate(r->io.ctx, m->index - 1)) {
                                r->failed = true;
                                return;
                            } else {
                                r->length = m->index - 1;
                                if (!rebuild_pending_graph(r))
                                    return;
                            }
                        }
                    }
                    if (ok && m->index > r->length) {
                        struct l5_entry e = {m->entry_term, m->event};
                        if (!r->io.append(r->io.ctx, e)) {
                            r->failed = true;
                            return;
                        }
                        r->length = m->index;
                        l5_apply(&r->pending_graph, e.event);
                    }
                    matched = m->index;
                }
            }
            if (ok) {
                if (r->replaying && m->commit > r->replay_until)
                    r->replay_until = m->commit;
                uint16_t commit = m->commit < matched ? m->commit : matched;
                if (commit > r->commit) {
                    r->commit = commit;
                    apply(r);
                }
            }
        }
        send(r, (struct l5_rpc){.type = L5_APPEND_REPLY,
                                .dst = m->src,
                                .success = ok,
                                .index = ok ? matched : r->length,
                                .prev_index = m->prev_index});
        return;
    }
    if (m->type == L5_APPEND_REPLY && r->role == L5_LEADER && m->term == r->term) {
        uint8_t n = m->src;
        if (m->success && m->index <= r->length) {
            /* Two buses/retries can deliver the same ACK more than once.
             * Only progress may launch the next entry: otherwise each duplicate
             * creates another APPEND/ACK chain during a long catch-up. */
            if (m->index <= r->match[n])
                return;
            r->match[n] = m->index;
            r->next[n] = m->index + 1;
            for (uint16_t i = r->length; i > r->commit; i--) {
                unsigned votes = 0;
                for (unsigned j = 1; j <= 3; j++)
                    votes += r->match[j] >= i;
                if (votes >= 2 && term_at(r, i) == r->term) {
                    r->commit = i;
                    apply(r);
                    broadcast_append(r);
                    break;
                }
            }
            if (r->next[n] <= r->length)
                append_to(r, n);
        } else if (!m->success && m->prev_index == r->next[n] - 1 && r->next[n] > 1) {
            uint16_t next = m->index + 1;
            r->next[n] = next < r->next[n] ? next : r->next[n] - 1;
            append_to(r, n);
        }
    }
}
