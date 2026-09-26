#ifndef CURRENT_SENSOR_H
#define CURRENT_SENSOR_H
#include <stdint.h>
void current_sensor_init(void);
uint16_t current_motor_left_ma(void);
uint16_t current_motor_right_ma(void);
uint16_t current_servo_ma(void);
#endif
