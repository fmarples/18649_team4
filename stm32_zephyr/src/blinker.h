#ifndef BLINKER_H
#define BLINKER_H
#include <stdint.h>
void blinker_init(void);
void blinker_update(int16_t steering, uint32_t buttons, int error_state);
#endif
