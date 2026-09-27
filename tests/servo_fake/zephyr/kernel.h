#ifndef FAKE_KERNEL_H
#define FAKE_KERNEL_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#define ARG_UNUSED(x) (void)(x)
#define K_NO_WAIT 0
struct k_msgq { size_t item, cap, count; unsigned char *data; };
#define K_MSGQ_DEFINE(name, size, count, align) \
 static unsigned char name##_data[(size) * (count)]; \
 struct k_msgq name = {size, count, 0, name##_data}
static inline int k_msgq_put(struct k_msgq *q, const void *data, int wait)
{
 (void)wait;
 if (q->count == q->cap) return -1;
 memcpy(q->data + q->count++ * q->item, data, q->item); return 0;
}
static inline int k_msgq_get(struct k_msgq *q, void *data, int wait)
{
 (void)wait;
 if (!q->count) return -1;
 memcpy(data, q->data, q->item); q->count--;
 memmove(q->data, q->data + q->item, q->count * q->item); return 0;
}
static inline void k_msgq_purge(struct k_msgq *q) { q->count = 0; }
extern uint64_t fake_now;
static inline uint64_t k_uptime_get(void) { return fake_now; }
int printk(const char *format, ...);
#endif
