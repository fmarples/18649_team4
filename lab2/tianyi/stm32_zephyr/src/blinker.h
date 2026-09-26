#ifndef BLINKER_H
#define BLINKER_H

#include <stdbool.h>

int blinker_init(void);
int blinker_set_left(bool on);
int blinker_set_right(bool on);
int blinker_set_hazard(bool on);

/* Button/steering state machine used for turn-signal self cancellation. */
int blinker_update(bool left_button, bool right_button, float steering_deg);

#endif
