#ifndef APP_STATE_H
#define APP_STATE_H

#include <stdint.h>

struct command_state {
    int16_t steering;
    int16_t throttle;
    int16_t brake;
    uint32_t buttons;
    uint16_t sequence;
    uint8_t valid;
};

struct status_state {
    uint16_t motor1_current;
    uint16_t motor2_current;
    uint16_t servo_current;
    uint8_t zone_state;
};

#endif
