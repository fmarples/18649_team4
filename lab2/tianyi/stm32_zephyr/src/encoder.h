#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

int encoder_init(void);
int32_t encoder_left_count(void);
int32_t encoder_right_count(void);
float encoder_left_velocity_mps(void);
float encoder_right_velocity_mps(void);
float encoder_get_average_velocity_mps(void);

#endif
