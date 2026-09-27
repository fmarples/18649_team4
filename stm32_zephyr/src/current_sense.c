#include "current_sense.h"
#include "schedule.h"
#include <zephyr/kernel.h>
K_MUTEX_DEFINE(current_mutex);
static struct current_sample latest; /* valid_mask is initially zero. */
K_THREAD_STACK_DEFINE(current_stack, 1536);
static struct k_work_q current_queue;
static struct k_work_delayable sample_work;
static int64_t next_sample_ms;
struct current_sample current_sense_snapshot(void)
{
    k_mutex_lock(&current_mutex, K_FOREVER);
    struct current_sample copy = latest;
    k_mutex_unlock(&current_mutex);
    return current_cache_snapshot(&copy, k_uptime_get_32(), CONFIG_LAB_CURRENT_MAX_AGE_MS);
}
static void sample_currents(struct k_work *work)
{
        ARG_UNUSED(work);
        int32_t ma[3] = {CURRENT_UNAVAILABLE, CURRENT_UNAVAILABLE, CURRENT_UNAVAILABLE};
        uint32_t mask = 0;
        /* Start timestamp conservatively includes acquisition/filter duration. */
        uint32_t started = k_uptime_get_32();
        int error = current_backend_read(ma, &mask);
        if (error != 0) mask = 0;
        struct current_sample sample;
        current_cache_publish(&sample, ma, mask, started);
        sample.error = error;
        k_mutex_lock(&current_mutex, K_FOREVER);
        latest = sample;
        k_mutex_unlock(&current_mutex);
        next_sample_ms += CONFIG_LAB_CURRENT_SAMPLE_MS;
        if (next_sample_ms <= k_uptime_get())
            next_sample_ms = k_uptime_get() + CONFIG_LAB_CURRENT_SAMPLE_MS;
        /* Own workqueue: a future ADC wait cannot delay system work or motor owner. */
        k_work_reschedule_for_queue(&current_queue, &sample_work,
                                    K_TIMEOUT_ABS_MS(next_sample_ms));
}
void current_sense_start(void)
{
    k_work_queue_start(&current_queue, current_stack, K_THREAD_STACK_SIZEOF(current_stack),
                       LAB_CURRENT_PRIORITY, NULL);
    k_work_init_delayable(&sample_work, sample_currents);
    next_sample_ms = k_uptime_get();
    k_work_schedule_for_queue(&current_queue, &sample_work, K_NO_WAIT);
}
