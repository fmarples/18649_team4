#ifndef MOTOR_H
#define MOTOR_H

int motor_init(void);
int motor_set_velocity(float left_mps, float right_mps);
int motor_dynamic_brake(void);

#endif
