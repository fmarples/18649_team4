#ifndef STEERING_H
#define STEERING_H
#include <stdint.h>
void steering_init(void);
void steering_set_from_wheel(int16_t wheel_value);
#endif
