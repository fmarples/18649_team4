#ifndef APP_STATE_H
#define APP_STATE_H

#include <stdint.h>
#include <stdbool.h>

/* Shared state between UART reception and the control tasks.
 * TODO: replace this simple example with a Zephyr mutex/message queue if
 * multiple fields can be updated/read concurrently on your final design. */
typedef struct {
    int16_t steering;
    int16_t throttle;
    int16_t brake;
    uint32_t buttons;
    uint16_t sequence;
    bool valid;
} command_state_t;

typedef enum {
    SYSTEM_ERROR = 0,
    SYSTEM_NORMAL = 1,
} system_state_t;

#endif
