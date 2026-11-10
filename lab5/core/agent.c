#include "agent.h"
#include <string.h>
static bool fresh(uint64_t now, uint64_t then, unsigned age) {
    return now >= then && now - then < age;
}
static uint8_t peers(struct l5_agent *a, unsigned bus, uint64_t ms, unsigned age) {
    uint8_t bits = 0;
    for (unsigned n = 1; n <= 3; n++)
        if (a->direct_seen[n][bus] && fresh(ms, a->direct[n][bus], age))
            bits |= 1U << (n - 1);
    return bits;
}
static void both(struct l5_agent *a, const struct l5_packet *p) {
    if (!a->paused)
        for (unsigned b = 0; b < 2; b++)
            a->send_packet(a->ctx, b, p);
}
void l5_agent_init(struct l5_agent *a, struct l5_raft *r, struct l5_clock *c, struct l5_wire *w,
                   void *ctx, void (*send)(void *, unsigned, const struct l5_packet *),
                   uint32_t delay) {
    memset(a, 0, sizeof(*a));
    a->raft = r;
    a->clock = c;
    a->wire = w;
    a->ctx = ctx;
    a->send_packet = send;
    a->delay_us = delay;
}
void l5_agent_rpc(struct l5_agent *a, const struct l5_rpc *m) {
    struct l5_packet p[4];
    l5_fragment(a->wire, m, p);
    for (unsigned i = 0; i < 4; i++)
        both(a, &p[i]);
}
static uint8_t source(const struct l5_packet *p) {
    if (p->id >= 0x410 && p->id <= 0x43f)
        return (p->id >> 4) & 3;
    if (p->id >= 0x81 && p->id <= 0x83)
        return p->id - 0x80;
    if (p->id >= 0x100 && p->id <= 0x102)
        return p->id - 0x100 + 1;
    if (p->id == 0x010 || p->id == 0x200)
        return 1;
    if (p->id == 0x300)
        return 2;
    if (p->id == 0x020)
        return p->data[3];
    return 0;
}
static void relay(struct l5_agent *a, unsigned bus, const struct l5_packet *p, uint64_t us) {
    uint64_t ms = us / 1000;
    uint8_t src = source(p), self = a->raft->id;
    unsigned other = bus ^ 1;
    /* A valid CRC does not make an untrusted FAULT reporter a valid node ID. */
    if (src < 1 || src > L5_NODES || src == self || a->paused ||
        !peers(a, 0, ms, 60) || !peers(a, 1, ms, 60))
        return;
    /* 40 ms discovery repair precedes the earliest 60 ms election timeout.
     * HELLO is never relayed: direct and indirect presence stay distinct. */
    if (a->direct_seen[src][other] && fresh(ms, a->direct[src][other], 40))
        return;
    uint8_t bridge = 0;
    bool route_known = false;
    for (uint8_t dst = 1; dst <= 3; dst++)
        if (dst != src && dst != self) {
            uint8_t candidate = 0;
            int first = l5_route(&a->raft->graph, src, dst, &candidate);
            if (first >= 0 && candidate) {
                bridge = candidate;
                route_known = true;
                break;
            }
        }
    if (!route_known ||
        (bridge != self && (!a->report_seen[bridge] || !fresh(ms, a->reports[bridge], 60)))) {
        bridge = self;
        for (uint8_t n = 1; n < self; n++)
            if (a->report_seen[n] && fresh(ms, a->reports[n], 60) && a->masks[n][0] &&
                a->masks[n][1]) {
                bridge = n;
                break;
            }
    }
    if (bridge != self)
        return;
    for (unsigned i = 0; i < 128; i++)
        if (a->seen[i].used && fresh(ms, a->seen[i].ms, 100) && a->seen[i].id == p->id &&
            !memcmp(a->seen[i].data, p->data, 8))
            return;
    struct l5_seen_packet *s = &a->seen[a->seen_next++ % 128];
    s->used = true;
    s->id = p->id;
    s->ms = ms;
    memcpy(s->data, p->data, 8);
    struct l5_packet out = *p;
    if (p->id >= 0x81 && p->id <= 0x83) {
        uint8_t n, cycle;
        uint16_t term;
        uint32_t t;
        if (l5_ref_unpack(p, &n, &cycle, &term, &t))
            l5_ref_pack(&out, n, cycle, term, t + a->delay_us);
    }
    a->send_packet(a->ctx, other, &out);
    a->relay_count++;
}
bool l5_agent_receive(struct l5_agent *a, unsigned bus, const struct l5_packet *p, uint64_t raw) {
    if (bus > 1)
        return true;
    uint64_t ms = raw / 1000;
    if (l5_crc(p->data, 7) != p->data[7])
        return p->id >= 0x400 || (p->id >= 0x80 && p->id < 0x100) ||
               (p->id >= 0x110 && p->id <= 0x113);
    if (p->id >= 0x111 && p->id <= 0x113) {
        uint8_t n = p->id - 0x110;
        if (n != a->raft->id) {
            a->direct[n][bus] = ms;
            a->direct_seen[n][bus] = true;
        }
        return true;
    }
    relay(a, bus, p, raw);
    if (p->id >= 0x81 && p->id <= 0x83) {
        uint8_t src, seq;
        uint16_t term;
        uint32_t t;
        if (a->paused || !l5_ref_unpack(p, &src, &seq, &term, &t) || src == a->raft->id)
            return true;
        if (a->ref_seen && src == a->rx_ref_src && term == a->rx_ref_term &&
            fresh(ms, a->last_ref, 250) &&
            ((uint8_t)(seq - a->rx_ref_seq) == 0 || (uint8_t)(seq - a->rx_ref_seq) >= 128))
            return true;
        if (l5_heartbeat(a->raft, src, term, ms) && (a->clock->synced || a->clock->have_epoch) &&
            l5_clock_ref(a->clock, src, term, t, raw, a->delay_us)) {
            a->last_ref = ms;
            a->rx_ref_seq = seq;
            a->rx_ref_src = src;
            a->rx_ref_term = term;
            a->ref_seen = true;
        }
        return true;
    }
    if (p->id >= 0x410 && p->id <= 0x43f) {
        struct l5_rpc m;
        if (a->paused || !l5_assemble(a->wire, p, ms, &m) || m.src == a->raft->id)
            return true;
        if (m.type == L5_REPORT) {
            if ((m.flags & 2) && m.term >= a->raft->term)
                a->held_events = m.index;
            if ((m.flags & 2) && m.term >= a->raft->term && !a->clock->synced) {
                a->clock->epoch_hint = (uint64_t)m.serial << 16;
                a->clock->have_epoch = true;
            }
            a->masks[m.src][0] = m.prev_index & 7;
            a->masks[m.src][1] = m.prev_term & 7;
            a->upstream[m.src] = m.flags & 1;
            a->reports[m.src] = ms;
            a->report_seen[m.src] = true;
        } else
            l5_receive(a->raft, &m, ms);
        return true;
    }
    return false;
}
static void observe_graph(struct l5_agent *a, uint64_t ms) {
    bool alive[4] = {0};
    uint8_t links = 0;
    for (uint8_t n = 1; n <= 3; n++)
        alive[n] = a->report_seen[n] && fresh(ms, a->reports[n], 66);
    for (uint8_t reporter = 1; reporter <= 3; reporter++)
        if (alive[reporter])
            for (unsigned b = 0; b < 2; b++) {
                uint8_t heard = a->masks[reporter][b];
                if (heard)
                    links |= 1U << (2 * (reporter - 1) + b);
                for (uint8_t n = 1; n <= 3; n++)
                    if (alive[n] && (heard & (1U << (n - 1))))
                        links |= 1U << (2 * (n - 1) + b);
            }
    for (uint8_t n = 1; n <= 3; n++) {
        (void)l5_request(a->raft, l5_node_event(n, alive[n]));
        if (alive[n])
            for (unsigned b = 0; b < 2; b++)
                (void)l5_request(a->raft,
                                 l5_link_event(n, b, (links & (1U << (2 * (n - 1) + b))) != 0));
    }
    (void)l5_request(a->raft, alive[1] && a->upstream[1] ? L5_COCKPIT_OK : L5_COCKPIT_ERROR);
}
void l5_agent_tick(struct l5_agent *a, uint64_t raw) {
    if (a->paused || a->raft->failed)
        return;
    uint64_t ms = raw / 1000;
    uint8_t self = a->raft->id;
    l5_tick(a->raft, ms);
    if (a->raft->role == L5_LEADER && (a->clock_leader != self || a->clock_term != a->raft->term)) {
        l5_clock_lead(a->clock, self, a->raft->term, raw);
        a->clock_leader = self;
        a->clock_term = a->raft->term;
    } else if (a->raft->role != L5_LEADER)
        a->clock_leader = 0;
    if (ms < a->next_periodic)
        return;
    a->next_periodic = ms + a->raft->cfg.heartbeat_ms;
    a->masks[self][0] = peers(a, 0, ms, 60);
    a->masks[self][1] = peers(a, 1, ms, 60);
    a->upstream[self] = a->upstream_ok;
    a->reports[self] = ms;
    a->report_seen[self] = true;
    if (a->raft->role == L5_LEADER)
        a->held_events = l5_held_events(a->raft);
    struct l5_packet hello = {.id = (uint16_t)(L5_HELLO_BASE + self),
                              .data = {a->hello_seq++, 0, 0, 0, 0, 0, 0, 0}};
    hello.data[7] = l5_crc(hello.data, 7);
    both(a, &hello);
    struct l5_rpc report = {.type = L5_REPORT,
                            .src = self,
                            .term = a->raft->term,
                            .prev_index = a->masks[self][0],
                            .prev_term = a->masks[self][1],
                            .index = a->held_events,
                            .flags =
                                (uint8_t)(a->upstream_ok | (a->raft->role == L5_LEADER ? 2 : 0)),
                            .serial = (uint32_t)(l5_global(a->clock, raw) >> 16)};
    l5_agent_rpc(a, &report);
    a->report_count++;
    if (a->raft->role == L5_LEADER) {
        struct l5_packet ref;
        l5_ref_pack(&ref, self, a->ref_seq++, a->raft->term, (uint32_t)l5_global(a->clock, raw));
        both(a, &ref);
        observe_graph(a, ms);
    }
}
bool l5_agent_error(const struct l5_agent *a, uint64_t raw) {
    uint64_t ms = raw / 1000;
    bool isolated = true;
    for (unsigned n = 1; n <= 3; n++)
        if (n != a->raft->id && a->report_seen[n] && fresh(ms, a->reports[n], 66))
            isolated = false;
    return a->paused || a->raft->failed || isolated || !a->report_seen[1] ||
           !fresh(ms, a->reports[1], 66) || !a->upstream[1];
}
unsigned l5_agent_hazard_hz(const struct l5_agent *a, uint64_t raw) {
    return a->report_seen[1] && fresh(raw / 1000, a->reports[1], 66) ? 2 : 4;
}
bool l5_agent_synced(const struct l5_agent *a, uint64_t raw) {
    return !a->paused && !a->raft->failed &&
           (a->raft->role == L5_LEADER || (a->ref_seen && fresh(raw / 1000, a->last_ref, 60)));
}
