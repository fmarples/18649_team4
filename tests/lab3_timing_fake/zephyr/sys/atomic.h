/* Single-threaded host substitute; these tests do not validate RTOS concurrency. */
#ifndef TEST_LAB3_ATOMIC_H
#define TEST_LAB3_ATOMIC_H
#include <stdbool.h>
#include <stdint.h>
typedef int32_t atomic_t;
typedef int32_t atomic_val_t;
static inline void atomic_set(atomic_t *p, atomic_val_t next) { *p = next; }
static inline atomic_val_t atomic_get(const atomic_t *p) { return *p; }
static inline atomic_val_t atomic_inc(atomic_t *p) { return (*p)++; }
static inline bool atomic_cas(atomic_t *p, atomic_val_t old, atomic_val_t next) {
    if (*p != old) return false;
    *p = next;
    return true;
}
#endif
