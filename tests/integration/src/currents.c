#include <zephyr/ztest.h>
#include "current_cache.h"

ZTEST(currents, test_boot_never_publishes_fake_zero)
{
    struct current_sample cache = {0};
    struct current_sample value = current_cache_snapshot(&cache, 0, 100);
    zassert_equal(value.valid_mask, 0);
    for (unsigned i = 0; i < 3; i++) zassert_equal(value.ma[i], CURRENT_UNAVAILABLE);
}
ZTEST(currents, test_channel_validity_and_signed_zero_measurements)
{
    struct current_sample cache;
    int32_t ma[3] = {0, -42, 100};
    current_cache_publish(&cache, ma, 0xFB, 20);
    struct current_sample value = current_cache_snapshot(&cache, 30, 100);
    zassert_equal(value.valid_mask, 3);
    zassert_equal(value.ma[0], 0); zassert_equal(value.ma[1], -42);
    zassert_equal(value.ma[2], CURRENT_UNAVAILABLE);
}
ZTEST(currents, test_age_limit_wrap_and_recovery)
{
    struct current_sample cache;
    int32_t ma[3] = {10, 20, 30};
    current_cache_publish(&cache, ma, 7, UINT32_MAX - 49);
    zassert_equal(current_cache_snapshot(&cache, 49, 100).valid_mask, 7);
    zassert_equal(current_cache_snapshot(&cache, 50, 100).valid_mask, 0);
    current_cache_publish(&cache, ma, 7, 51);
    zassert_equal(current_cache_snapshot(&cache, 51, 100).valid_mask, 7);
}
ZTEST(currents, test_invalid_sentinel_and_failed_replacement)
{
    struct current_sample cache;
    int32_t ma[3] = {CURRENT_UNAVAILABLE, 200, 300};
    current_cache_publish(&cache, ma, 7, 0);
    zassert_equal(cache.valid_mask, 6);
    current_cache_publish(&cache, ma, 0, 20);
    struct current_sample value = current_cache_snapshot(&cache, 20, 100);
    zassert_equal(value.valid_mask, 0);
    for (unsigned i = 0; i < 3; i++) zassert_equal(value.ma[i], CURRENT_UNAVAILABLE);
}
ZTEST_SUITE(currents, NULL, NULL, NULL, NULL, NULL);
