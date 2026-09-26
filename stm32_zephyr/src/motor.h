#ifndef MOTOR_H
#define MOTOR_H
#include <stdint.h>
void motor_init(void);
void motor_set_pwm(uint8_t left_percent, uint8_t right_percent);
void motor_set_direction(bool forward);
void motor_dynamic_brake(void);
void motor_disable(void);
#endif
