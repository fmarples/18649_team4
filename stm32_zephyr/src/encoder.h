#ifndef ENCODER_H
#define ENCODER_H
#include <stdint.h>
void encoder_init(void);
int32_t encoder_get_left_count(void);
int32_t encoder_get_right_count(void);
float encoder_get_average_velocity_mps(void);
#endif
