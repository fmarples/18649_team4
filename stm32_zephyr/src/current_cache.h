#ifndef LAB_CURRENT_CACHE_H
#define LAB_CURRENT_CACHE_H
#include <stdint.h>
#define CURRENT_CHANNELS 3
#define CURRENT_UNAVAILABLE INT32_MIN
/* Channel order: left motor, right motor, servo. */
struct current_sample { int32_t ma[CURRENT_CHANNELS]; uint32_t valid_mask, sampled_ms; };
void current_cache_publish(struct current_sample *cache, const int32_t ma[3],
                           uint32_t valid_mask, uint32_t sampled_ms);
struct current_sample current_cache_snapshot(const struct current_sample *cache,
                                            uint32_t now_ms, uint32_t max_age_ms);
#endif
