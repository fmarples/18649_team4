#include "current_cache.h"
void current_cache_publish(struct current_sample *cache, const int32_t ma[3],
                           uint32_t valid_mask, uint32_t sampled_ms)
{
    cache->error = 0;
    cache->valid_mask = valid_mask & 7U;
    cache->sampled_ms = sampled_ms;
    for (unsigned i = 0; i < CURRENT_CHANNELS; i++) {
        if (ma[i] == CURRENT_UNAVAILABLE) cache->valid_mask &= ~(1U << i);
        cache->ma[i] = cache->valid_mask & (1U << i) ? ma[i] : CURRENT_UNAVAILABLE;
    }
}
struct current_sample current_cache_snapshot(const struct current_sample *cache,
                                            uint32_t now_ms, uint32_t max_age_ms)
{
    struct current_sample result = *cache;
    if ((uint32_t)(now_ms - cache->sampled_ms) >= max_age_ms) result.valid_mask = 0;
    for (unsigned i = 0; i < CURRENT_CHANNELS; i++)
        if (!(result.valid_mask & (1U << i))) result.ma[i] = CURRENT_UNAVAILABLE;
    return result;
}
