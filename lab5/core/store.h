#ifndef LAB5_STORE_H
#define LAB5_STORE_H
#include "lab5.h"
/* Two 128 KiB erase units. 30,000 x 4-byte records per bank, no RAM log.
 * Callback offsets are relative to the combined 256 KiB storage region. */
#define L5_BANK_SIZE 131072U
#define L5_STORE_SIZE (2U * L5_BANK_SIZE)
#define L5_DATA_OFFSET 2048U
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
};
bool l5_store_open(struct l5_store *, struct l5_flash_io);
/* Boot-only maintenance, before real-time tasks/watchdog: reclaim a full
 * term/vote journal without changing its logical contents. */
bool l5_store_prepare_boot(struct l5_store *);
bool l5_store_read(void *, uint16_t, struct l5_entry *);
bool l5_store_append(void *, struct l5_entry);
bool l5_store_truncate(void *, uint16_t);
bool l5_store_hardstate(void *, uint16_t, uint8_t);
#endif
