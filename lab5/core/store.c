#include "store.h"
#include <string.h>
#define MAGIC 0x35474f4cU
#define JOURNAL_START 16U
#define JOURNAL_SLOTS ((L5_DATA_OFFSET - JOURNAL_START) / 4U)
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
        if (!rd(s, s->bank * L5_BANK_SIZE + L5_DATA_OFFSET + 4U * i, &w, 4) || !valid(w)) {
            s->failed = true;
            return false;
        }
        if (!wr(s, base + L5_DATA_OFFSET + 4U * i, &w, 4))
            return false;
    }
    /* Activate LAST. Until this succeeds, the old bank is authoritative. */
    if (!wr(s, base, h, 4))
        return false;
    s->bank = (uint8_t)b;
    s->generation = h[1];
    s->length = retained;
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
    for (unsigned i = 0; i < L5_CAPACITY; i++) {
        if (!rd(s, base + L5_DATA_OFFSET + 4 * i, &w, 4))
            return false;
        if (w == UINT32_MAX)
            break;
        if (!valid(w) || (uint16_t)w == 0 || (uint16_t)w > s->term ||
            ((w >> 16) & 255) > L5_EVENT_MAX) {
            s->failed = true;
            return false;
        }
        s->length = i + 1;
    }
    return true;
}
bool l5_store_read(void *ctx, uint16_t i, struct l5_entry *e) {
    struct l5_store *s = ctx;
    uint32_t w;
    if (!i || i > s->length ||
        !rd(s, s->bank * L5_BANK_SIZE + L5_DATA_OFFSET + 4U * (i - 1), &w, 4) || !valid(w))
        return false;
    e->term = (uint16_t)w;
    e->event = (uint8_t)(w >> 16);
    return true;
}
bool l5_store_prepare_boot(struct l5_store *s) {
    if (s->failed)
        return false;
    if (s->journal < JOURNAL_SLOTS)
        return true;
    return compact(s, s->length, s->term, s->vote);
}
bool l5_store_append(void *ctx, struct l5_entry e) {
    struct l5_store *s = ctx;
    if (s->failed || s->length >= L5_CAPACITY || !e.term || e.term > s->term ||
        e.event > L5_EVENT_MAX)
        return false;
    uint32_t w = record(e.term, e.event);
    if (!wr(s, s->bank * L5_BANK_SIZE + L5_DATA_OFFSET + 4U * s->length, &w, 4))
        return false;
    s->length++;
    return true;
}
bool l5_store_truncate(void *ctx, uint16_t retained) {
    struct l5_store *s = ctx;
    if (s->failed || retained > s->length)
        return false;
    if (retained == s->length)
        return true;
    return compact(s, retained, s->term, s->vote);
}
bool l5_store_hardstate(void *ctx, uint16_t term, uint8_t vote) {
    struct l5_store *s = ctx;
    if (s->failed || term < s->term || term > L5_TERM_MAX || vote > 3)
        return false;
    if (term == s->term && vote == s->vote)
        return true;
    if (s->journal >= JOURNAL_SLOTS)
        return compact(s, s->length, term, vote);
    uint32_t w = record(term, vote);
    if (!wr(s, s->bank * L5_BANK_SIZE + JOURNAL_START + 4U * s->journal, &w, 4))
        return false;
    s->term = term;
    s->vote = vote;
    s->journal++;
    return true;
}
