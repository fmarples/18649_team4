#ifndef LAB5_STORE_H
#define LAB5_STORE_H
#include "lab5.h"
/* Two 128 KiB erase units. 30,000 x 4-byte records per bank, no RAM log.
 * Callback offsets are relative to the combined 256 KiB storage region. */
#define L5_BANK_SIZE 131072U
#define L5_STORE_SIZE (2U * L5_BANK_SIZE)
#define L5_DATA_OFFSET 2048U
#define L5_STORE_SLOTS ((L5_BANK_SIZE - L5_DATA_OFFSET) / 4U)
#define L5_STORE_WORDS (L5_STORE_SLOTS / 32U)
struct l5_flash_io {
    void *ctx;
    bool (*read)(void *, uint32_t, void *, size_t);
    bool (*write)(void *, uint32_t, const void *, size_t);
    bool (*erase)(void *, unsigned bank);
};
struct l5_store {
    struct l5_flash_io io;
    uint32_t generation;
    uint16_t length, term, journal;
    uint8_t bank, vote;
    bool failed;
    uint16_t used;
    /* Active entry positions, not a RAM copy of the log. The count tree
     * selects a logical index in O(log(words)) after suffix rollback. */
    uint32_t active[L5_STORE_WORDS];
    uint16_t counts[L5_STORE_WORDS + 1];
};
bool l5_store_open(struct l5_store *, struct l5_flash_io);
/* Boot-only maintenance, before real-time tasks/watchdog: reclaim obsolete
 * suffixes and a full term/vote journal without changing logical contents.
 * Runtime mutations only program fresh words; none erase a flash sector. */
bool l5_store_prepare_boot(struct l5_store *);
bool l5_store_read(void *, uint16_t, struct l5_entry *);
bool l5_store_append(void *, struct l5_entry);
bool l5_store_truncate(void *, uint16_t);
bool l5_store_hardstate(void *, uint16_t, uint8_t);
#endif
