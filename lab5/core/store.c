#include "store.h"
#include <string.h>
#define MAGIC 0x35474f4cU
#define JOURNAL_START 16U
#define JOURNAL_SLOTS ((L5_DATA_OFFSET - JOURNAL_START) / 4U)
/* Legacy term/event banks remain readable. Reserved event values append
 * rollback/hard-state metadata; old firmware refuses these records, so do
 * not downgrade against a bank containing them. */
#define ROLLBACK 254U
#define HARDSTATE 240U
static void activate(struct l5_store *s, unsigned slot) {
    unsigned word = slot / 32U;
    s->active[word] |= 1U << (slot % 32U);
    for (unsigned i = word + 1; i <= L5_STORE_WORDS; i += i & -i)
        s->counts[i]++;
}
static unsigned position(struct l5_store *s, unsigned index) {
    unsigned word = 0;
    /* Fenwick lower_bound: skip groups containing fewer than index entries. */
    for (unsigned step = 1024; step; step >>= 1) {
        unsigned next = word + step;
        if (next <= L5_STORE_WORDS && s->counts[next] < index) {
            index -= s->counts[next];
            word = next;
        }
    }
    uint32_t bits = s->active[word];
    while (--index)
        bits &= bits - 1;
    return word * 32U + (unsigned)__builtin_ctz(bits);
}
static void retain(struct l5_store *s, unsigned length) {
    unsigned end = length ? position(s, length) + 1 : 0;
    unsigned word = end / 32U, bit = end % 32U;
    if (bit)
        s->active[word++] &= (1U << bit) - 1;
    memset(s->active + word, 0, (L5_STORE_WORDS - word) * sizeof(s->active[0]));
    memset(s->counts, 0, sizeof(s->counts));
    for (unsigned i = 1; i <= L5_STORE_WORDS; i++) {
        s->counts[i] += (uint16_t)__builtin_popcount(s->active[i - 1]);
        unsigned parent = i + (i & -i);
        if (parent <= L5_STORE_WORDS)
            s->counts[parent] += s->counts[i];
    }
    s->length = (uint16_t)length;
}
static void canonical_positions(struct l5_store *s, unsigned length) {
    memset(s->active, 0, sizeof(s->active));
    memset(s->counts, 0, sizeof(s->counts));
    for (unsigned i = 0; i < length; i++)
        activate(s, i);
    s->used = s->length = (uint16_t)length;
}
static bool rd(struct l5_store *s, uint32_t o, void *p, size_t n) {
    return s->io.read(s->io.ctx, o, p, n);
}
static bool wr(struct l5_store *s, uint32_t o, const void *p, size_t n) {
    bool ok = s->io.write(s->io.ctx, o, p, n);
    if (!ok)
        s->failed = true;
    return ok;
}
static uint32_t record(uint16_t t, uint8_t v) {
    uint8_t p[3] = {(uint8_t)t, (uint8_t)(t >> 8), v};
    return t | ((uint32_t)v << 16) | ((uint32_t)l5_crc(p, 3) << 24);
}
static bool valid(uint32_t w) {
    return w != UINT32_MAX && w == record((uint16_t)w, (uint8_t)(w >> 16));
}
static bool header(struct l5_store *s, unsigned bank, uint32_t h[4]) {
    if (!rd(s, bank * L5_BANK_SIZE, h, 16))
        return false;
    return h[0] == MAGIC && h[2] == ~h[1] && h[3] == (uint32_t)l5_crc((uint8_t *)(h + 1), 8);
}
static bool compact(struct l5_store *s, uint16_t retained, uint16_t term, uint8_t vote) {
    unsigned b = s->bank ^ 1U;
    uint32_t base = b * L5_BANK_SIZE;
    if (!s->io.erase(s->io.ctx, b)) {
        s->failed = true;
        return false;
    }
    uint32_t h[4] = {MAGIC, s->generation + 1, ~(s->generation + 1), 0};
    h[3] = l5_crc((uint8_t *)(h + 1), 8);
    if (!wr(s, base + 4, h + 1, 12))
        return false;
    uint32_t w = record(term, vote);
    if (!wr(s, base + JOURNAL_START, &w, 4))
        return false;
    for (uint16_t i = 0; i < retained; i++) {
        struct l5_entry e;
        if (!l5_store_read(s, i + 1, &e)) {
            s->failed = true;
            return false;
        }
        w = record(e.term, e.event);
        if (!wr(s, base + L5_DATA_OFFSET + 4U * i, &w, 4))
            return false;
    }
    /* Activate LAST. Until this succeeds, the old bank is authoritative. */
    if (!wr(s, base, h, 4))
        return false;
    s->bank = (uint8_t)b;
    s->generation = h[1];
    canonical_positions(s, retained);
    s->term = term;
    s->vote = vote;
    s->journal = 1;
    return true;
}
bool l5_store_open(struct l5_store *s, struct l5_flash_io io) {
    memset(s, 0, sizeof(*s));
    s->io = io;
    uint32_t h[2][4];
    bool a = header(s, 0, h[0]), b = header(s, 1, h[1]);
    if (!a && !b) {
        /* Do not silently erase unrecognised/corrupt persisted state. */
        uint32_t w;
        for (uint32_t o = 0; o < L5_STORE_SIZE; o += 4)
            if (!rd(s, o, &w, 4) || w != UINT32_MAX) {
                s->failed = true;
                return false;
            }
        s->bank = 1;
        return compact(s, 0, 0, 0);
    }
    s->bank = b && (!a || h[1][1] > h[0][1]);
    s->generation = h[s->bank][1];
    uint32_t base = s->bank * L5_BANK_SIZE, w;
    for (unsigned j = 0; j < JOURNAL_SLOTS; j++) {
        if (!rd(s, base + JOURNAL_START + 4 * j, &w, 4))
            return false;
        if (w == UINT32_MAX)
            break;
        if (!valid(w) || (uint16_t)w > L5_TERM_MAX || ((w >> 16) & 255) > 3) {
            s->failed = true;
            return false;
        }
        s->term = (uint16_t)w;
        s->vote = (uint8_t)(w >> 16);
        s->journal = j + 1;
    }
    if (!s->journal) {
        s->failed = true;
        return false;
    }
    for (unsigned i = 0; i < L5_STORE_SLOTS; i++) {
        if (!rd(s, base + L5_DATA_OFFSET + 4 * i, &w, 4))
            return false;
        if (w == UINT32_MAX)
            break;
        uint16_t t = (uint16_t)w;
        uint8_t v = (uint8_t)(w >> 16);
        if (!valid(w)) {
            s->failed = true;
            return false;
        }
        if (v == ROLLBACK && t <= s->length) {
            retain(s, t);
        } else if (v >= HARDSTATE && v <= HARDSTATE + 3 &&
                   s->journal == JOURNAL_SLOTS && t >= s->term && t <= L5_TERM_MAX) {
            s->term = t;
            s->vote = v - HARDSTATE;
        } else if (v <= L5_EVENT_MAX && t && t <= s->term && s->length < L5_CAPACITY) {
            activate(s, i);
            s->length++;
        } else {
            s->failed = true;
            return false;
        }
        s->used = i + 1;
    }
    return true;
}
bool l5_store_read(void *ctx, uint16_t i, struct l5_entry *e) {
    struct l5_store *s = ctx;
    uint32_t w;
    if (!i || i > s->length ||
        !rd(s, s->bank * L5_BANK_SIZE + L5_DATA_OFFSET + 4U * position(s, i), &w, 4) || !valid(w))
        return false;
    e->term = (uint16_t)w;
    e->event = (uint8_t)(w >> 16);
    return true;
}
bool l5_store_prepare_boot(struct l5_store *s) {
    if (s->failed)
        return false;
    if (s->journal < JOURNAL_SLOTS && s->used == s->length)
        return true;
    return compact(s, s->length, s->term, s->vote);
}
static bool append_word(struct l5_store *s, uint32_t w) {
    if (s->used >= L5_STORE_SLOTS) {
        s->failed = true;
        return false;
    }
    if (!wr(s, s->bank * L5_BANK_SIZE + L5_DATA_OFFSET + 4U * s->used, &w, 4))
        return false;
    s->used++;
    return true;
}
bool l5_store_append(void *ctx, struct l5_entry e) {
    struct l5_store *s = ctx;
    if (s->failed || s->length >= L5_CAPACITY || !e.term || e.term > s->term ||
        e.event > L5_EVENT_MAX)
        return false;
    uint32_t w = record(e.term, e.event);
    if (!append_word(s, w))
        return false;
    activate(s, s->used - 1);
    s->length++;
    return true;
}
bool l5_store_truncate(void *ctx, uint16_t retained) {
    struct l5_store *s = ctx;
    if (s->failed || retained > s->length)
        return false;
    if (retained == s->length)
        return true;
    /* Durable marker first: a restart reconstructs exactly this rollback.
     * Keep old words intact and place subsequent entries at fresh addresses. */
    if (!append_word(s, record(retained, ROLLBACK)))
        return false;
    retain(s, retained);
    return true;
}
bool l5_store_hardstate(void *ctx, uint16_t term, uint8_t vote) {
    struct l5_store *s = ctx;
    if (s->failed || term < s->term || term > L5_TERM_MAX || vote > 3)
        return false;
    if (term == s->term && vote == s->vote)
        return true;
    if (s->journal >= JOURNAL_SLOTS) {
        if (!append_word(s, record(term, HARDSTATE + vote)))
            return false;
        s->term = term;
        s->vote = vote;
        return true;
    }
    uint32_t w = record(term, vote);
    if (!wr(s, s->bank * L5_BANK_SIZE + JOURNAL_START + 4U * s->journal, &w, 4))
        return false;
    s->term = term;
    s->vote = vote;
    s->journal++;
    return true;
}
