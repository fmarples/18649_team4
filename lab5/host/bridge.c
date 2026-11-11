/* Host ABI uses the exact production C core and flash journal. No Raft model
 * is substituted in Python. Linux file writes are fsync'd before ACK/voting. */
#include "agent.h"
#include "lab5.h"
#include "store.h"
#include "wire.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <io.h>
#define API __declspec(dllexport)
#define SYNC(f) _commit(_fileno(f))
#else
#include <unistd.h>
#define API __attribute__((visibility("default")))
#define SYNC(f) fsync(fileno(f))
#endif
#define Q 2048
/* A single APPEND can confirm the entire saved prefix after restart. Applied
 * notifications cannot share the smaller transport queue's loss policy.
 * Each log index is applied once per host lifetime, so the configured maximum
 * log length also bounds the total number of outstanding notifications. This
 * storage is host/Pi-only; it does not consume Nucleo RAM. */
#define APPLIED_Q L5_CAPACITY
struct applied {
    uint16_t index, term;
    uint8_t event, replay;
};
struct host {
    struct l5_raft raft;
    struct l5_store store;
    struct l5_clock clock;
    struct l5_wire wire;
    uint8_t bytes[L5_STORE_SIZE];
    FILE *file;
    struct l5_rpc tx[Q];
    unsigned head, tail;
    struct applied applied[APPLIED_Q];
    unsigned ah, at;
    unsigned dropped;
    unsigned entry_reads;
    int fail_write;
    struct l5_agent agent;
    bool agent_enabled;
    struct l5_packet packets[Q];
    uint8_t buses[Q];
    unsigned ph, pt;
};
static bool read_flash(void *v, uint32_t off, void *p, size_t n) {
    struct host *h = v;
    if (off + n > L5_STORE_SIZE)
        return false;
    memcpy(p, h->bytes + off, n);
    return true;
}
static bool persist(struct host *h, uint32_t off, size_t n) {
    if (!h->file)
        return true;
    return fseek(h->file, (long)off, SEEK_SET) == 0 && fwrite(h->bytes + off, 1, n, h->file) == n &&
           fflush(h->file) == 0 && SYNC(h->file) == 0;
}
static bool write_flash(void *v, uint32_t off, const void *p, size_t n) {
    struct host *h = v;
    const uint8_t *b = p;
    if (h->fail_write == 0)
        return false;
    if (h->fail_write > 0)
        h->fail_write--;
    if (off + n > L5_STORE_SIZE)
        return false;
    for (size_t i = 0; i < n; i++)
        if ((h->bytes[off + i] & b[i]) != b[i])
            return false;
    memcpy(h->bytes + off, p, n);
    return persist(h, off, n);
}
static bool erase_flash(void *v, unsigned bank) {
    struct host *h = v;
    if (h->fail_write == 0 || bank > 1)
        return false;
    if (h->fail_write > 0)
        h->fail_write--;
    memset(h->bytes + bank * L5_BANK_SIZE, 255, L5_BANK_SIZE);
    return persist(h, bank * L5_BANK_SIZE, L5_BANK_SIZE);
}
static bool read_entry(void *v, uint16_t i, struct l5_entry *e) {
    ((struct host *)v)->entry_reads++;
    return l5_store_read(&((struct host *)v)->store, i, e);
}
static bool append_entry(void *v, struct l5_entry e) {
    return l5_store_append(&((struct host *)v)->store, e);
}
static bool truncate_entries(void *v, uint16_t i) {
    return l5_store_truncate(&((struct host *)v)->store, i);
}
static bool hard_state(void *v, uint16_t t, uint8_t n) {
    return l5_store_hardstate(&((struct host *)v)->store, t, n);
}
static void emit(void *v, const struct l5_rpc *m) {
    struct host *h = v;
    if (h->agent_enabled) {
        l5_agent_rpc(&h->agent, m);
        return;
    }
    if (h->head - h->tail >= Q) {
        h->dropped++;
        return;
    }
    h->tx[h->head++ % Q] = *m;
}
static void applied(void *v, uint16_t i, struct l5_entry e, bool replay) {
    struct host *h = v;
    if (h->ah - h->at >= APPLIED_Q) {
        h->dropped++;
        return;
    }
    h->applied[h->ah++ % APPLIED_Q] = (struct applied){i, e.term, e.event, replay};
}
API void *l5_host_new(unsigned id, unsigned leader, unsigned seed, unsigned capacity,
                      const char *path) {
    struct host *h = calloc(1, sizeof(*h));
    if (!h)
        return NULL;
    h->fail_write = -1;
    memset(h->bytes, 255, sizeof(h->bytes));
    if (path && *path) {
        h->file = fopen(path, "r+b");
        if (h->file) {
            if (fread(h->bytes, 1, sizeof(h->bytes), h->file) != sizeof(h->bytes)) {
                fclose(h->file);
                free(h);
                return NULL;
            }
        } else {
            h->file = fopen(path, "w+b");
            if (!h->file || !persist(h, 0, sizeof(h->bytes))) {
                if (h->file)
                    fclose(h->file);
                free(h);
                return NULL;
            }
        }
    }
    struct l5_flash_io flash = {h, read_flash, write_flash, erase_flash};
    struct l5_io io = {h, read_entry, append_entry, truncate_entries, hard_state, emit, applied};
    struct l5_config cfg = {20, 100, 3, 39, (uint16_t)capacity, (uint8_t)leader, seed, false};
    if (!l5_store_open(&h->store, flash) || !l5_init(&h->raft, (uint8_t)id, cfg, io, h->store.term,
                                                     h->store.vote, h->store.length, 0)) {
        if (h->file)
            fclose(h->file);
        free(h);
        return NULL;
    }
    l5_clock_init(&h->clock, 0);
    return h;
}
API void l5_host_free(void *v) {
    struct host *h = v;
    if (h->file)
        fclose(h->file);
    free(h);
}
API void l5_host_tick(void *v, uint64_t ms) { l5_tick(&((struct host *)v)->raft, ms); }
API int l5_host_request(void *v, unsigned event) {
    return l5_request(&((struct host *)v)->raft, (uint8_t)event);
}
API int l5_host_user_event(void *v) { return l5_user_event(&((struct host *)v)->raft); }
API void l5_host_receive(void *v, const uint8_t *p, uint64_t ms) {
    struct l5_rpc m;
    if (l5_decode(&m, p))
        l5_receive(&((struct host *)v)->raft, &m, ms);
}
API int l5_host_drain(void *v, uint8_t *p) {
    struct host *h = v;
    if (h->head == h->tail)
        return 0;
    l5_encode(&h->tx[h->tail++ % Q], p);
    return 1;
}
API int l5_host_applied(void *v, uint16_t *p) {
    struct host *h = v;
    if (h->ah == h->at)
        return 0;
    struct applied a = h->applied[h->at++ % APPLIED_Q];
    p[0] = a.index;
    p[1] = a.term;
    p[2] = a.event;
    p[3] = a.replay;
    return 1;
}
API unsigned l5_host_status(void *v, unsigned field) {
    struct host *h = v;
    struct l5_raft *r = &h->raft;
    switch (field) {
    case 0:
        return r->role;
    case 1:
        return r->term;
    case 2:
        return r->leader;
    case 3:
        return r->length;
    case 4:
        return r->commit;
    case 5:
        return r->applied;
    case 6:
        return r->graph.nodes;
    case 7:
        return r->graph.links;
    case 8:
        return r->graph.cockpit_ok;
    case 9:
        return r->failed;
    case 10:
        return h->dropped;
    case 11:
        return r->vote;
    case 12:
        return h->entry_reads;
    default:
        return 0;
    }
}
API int l5_host_entry(void *v, unsigned i, uint16_t *out) {
    struct l5_entry e;
    if (!read_entry(v, (uint16_t)i, &e))
        return 0;
    out[0] = e.term;
    out[1] = e.event;
    return 1;
}
API int l5_host_heartbeat(void *v, unsigned src, unsigned term, uint64_t ms) {
    return l5_heartbeat(&((struct host *)v)->raft, (uint8_t)src, (uint16_t)term, ms);
}
API void l5_host_fail_write(void *v, int after) { ((struct host *)v)->fail_write = after; }
API int l5_host_reopen(void *v) {
    struct host *h = v;
    return l5_store_open(&h->store, h->store.io);
}
API int l5_host_truncate(void *v, unsigned len) {
    return l5_store_truncate(&((struct host *)v)->store, (uint16_t)len);
}
API unsigned l5_host_store_length(void *v) { return ((struct host *)v)->store.length; }
API unsigned l5_host_held_events(void *v) { return l5_held_events(&((struct host *)v)->raft); }
API int l5_host_store_prepare_boot(void *v) {
    return l5_store_prepare_boot(&((struct host *)v)->store);
}
API int l5_host_store_hardstate(void *v, unsigned term, unsigned vote) {
    return l5_store_hardstate(&((struct host *)v)->store, (uint16_t)term, (uint8_t)vote);
}
API unsigned l5_host_store_state(void *v, unsigned field) {
    struct l5_store *s = &((struct host *)v)->store;
    switch (field) {
    case 0: return s->term;
    case 1: return s->vote;
    case 2: return s->journal;
    case 3: return s->generation;
    default: return 0;
    }
}
API int l5_host_store_append(void *v, unsigned term, unsigned event) {
    return l5_store_append(&((struct host *)v)->store, (struct l5_entry){term, event});
}
API void l5_host_fragment(void *v, const uint8_t *p, uint8_t *out) {
    struct host *h = v;
    struct l5_rpc m;
    struct l5_packet f[4];
    if (!l5_decode(&m, p))
        return;
    l5_fragment(&h->wire, &m, f);
    for (unsigned i = 0; i < 4; i++) {
        out[i * 10] = (uint8_t)f[i].id;
        out[i * 10 + 1] = (uint8_t)(f[i].id >> 8);
        memcpy(out + i * 10 + 2, f[i].data, 8);
    }
}
API int l5_host_packet(void *v, unsigned bus, unsigned id, const uint8_t *p, uint64_t ms, uint8_t *out) {
    struct host *h = v;
    struct l5_packet f = {.id = (uint16_t)id};
    struct l5_rpc m;
    memcpy(f.data, p, 8);
    if (!l5_assemble(&h->wire, bus, &f, ms, &m))
        return 0;
    l5_encode(&m, out);
    return 1;
}
API uint64_t l5_host_global(void *v, uint64_t us) {
    return l5_global(&((struct host *)v)->clock, us);
}
API int l5_host_ref(void *v, unsigned src, unsigned term, uint32_t low, uint64_t raw,
                    unsigned delay) {
    return l5_clock_ref(&((struct host *)v)->clock, (uint8_t)src, (uint16_t)term, low, raw, delay);
}
API void l5_host_lead(void *v, unsigned src, unsigned term, uint64_t raw) {
    l5_clock_lead(&((struct host *)v)->clock, (uint8_t)src, (uint16_t)term, raw);
}
API double l5_host_rate(void *v) { return ((struct host *)v)->clock.rate; }
API unsigned l5_host_clock_samples(void *v) { return ((struct host *)v)->clock.samples; }
API int64_t l5_host_correction(void *v, uint64_t raw) {
    struct l5_clock *c = &((struct host *)v)->clock;
    return (int64_t)((raw - c->local_anchor) * (c->rate - 1.0));
}
API void l5_host_queue_delay(void *v, unsigned delay) {
    ((struct host *)v)->agent.delay_us = delay;
}
API int l5_host_route(void *v, unsigned src, unsigned dst, unsigned *bridge) {
    uint8_t b = 0;
    int bus = l5_route(&((struct host *)v)->raft.graph, (uint8_t)src, (uint8_t)dst, &b);
    *bridge = b;
    return bus;
}
static void packet_out(void *v, unsigned bus, const struct l5_packet *p) {
    struct host *h = v;
    if (h->ph - h->pt >= Q) {
        h->dropped++;
        return;
    }
    unsigned slot = h->ph++ % Q;
    h->packets[slot] = *p;
    h->buses[slot] = (uint8_t)bus;
}
API void l5_host_agent_enable(void *v, unsigned delay) {
    struct host *h = v;
    l5_agent_init(&h->agent, &h->raft, &h->clock, &h->wire, h, packet_out, delay);
    h->agent_enabled = true;
    while (h->head != h->tail)
        l5_agent_rpc(&h->agent, &h->tx[h->tail++ % Q]);
}
API void l5_host_agent_tick(void *v, uint64_t us, unsigned upstream, unsigned paused) {
    struct host *h = v;
    h->agent.upstream_ok = upstream;
    h->agent.paused = paused;
    l5_agent_tick(&h->agent, us);
}
API int l5_host_agent_receive(void *v, unsigned bus, unsigned id, const uint8_t *p, uint64_t us) {
    struct host *h = v;
    struct l5_packet f = {.id = (uint16_t)id};
    memcpy(f.data, p, 8);
    return l5_agent_receive(&h->agent, bus, &f, us);
}
API int l5_host_agent_drain(void *v, uint16_t *meta, uint8_t *p) {
    struct host *h = v;
    if (h->ph == h->pt)
        return 0;
    unsigned slot = h->pt++ % Q;
    meta[0] = h->buses[slot];
    meta[1] = h->packets[slot].id;
    memcpy(p, h->packets[slot].data, 8);
    return 1;
}
API unsigned l5_host_agent_status(void *v, unsigned field, uint64_t us) {
    struct host *h = v;
    switch (field) {
    case 0:
        return l5_agent_error(&h->agent, us);
    case 1:
        return l5_agent_hazard_hz(&h->agent, us);
    case 2:
        return l5_agent_synced(&h->agent, us);
    case 3:
        return h->agent.relay_count;
    case 4:
        return h->agent.held_events;
    default:
        return 0;
    }
}
