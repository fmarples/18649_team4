#ifndef LAB_SCHEDULE_H
#define LAB_SCHEDULE_H
#include <stdbool.h>
#include <stdint.h>
/* All threads are preemptible. Lower numbers have higher priority. */
#define LAB_STATUS_PRIORITY 2
#define LAB_CURRENT_PRIORITY 3
#define LAB_CONSOLE_PRIORITY 4
#define LAB_OWNER_WAIT_MS 1
#define LAB_STATUS_PERIOD_MS 20
#define LAB_COMMAND_PERIOD_MS 20
#define LAB_LINK_TIMEOUT_MS (3 * LAB_COMMAND_PERIOD_MS)
#define LAB_CONSOLE_POLL_MS 10
#define LAB_DIAGNOSTIC_PERIOD_MS 250
static inline bool lab_link_expired(uint32_t now_ms, uint32_t received_ms)
{
    return (uint32_t)(now_ms - received_ms) >= LAB_LINK_TIMEOUT_MS;
}
#endif
