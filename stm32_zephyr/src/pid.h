#ifndef PID_H
#define PID_H
typedef struct { float kp, ki, kd; float integral; float previous_error; } pid_t;
void pid_init(pid_t *p, float kp, float ki, float kd);
float pid_update(pid_t *p, float target, float measured, float dt_s);
#endif
