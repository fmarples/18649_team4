#ifndef LAB2_BLINKER_GPIO_H
#define LAB2_BLINKER_GPIO_H
#include "blinker_core.h"
int blinker_gpio_init(void);
int blinker_gpio_write(struct blink_output output);
#endif
