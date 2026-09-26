#include "pid.h"
void pid_init(pid_t *p, float kp, float ki, float kd) {
    p->kp=kp; p->ki=ki; p->kd=kd; p->integral=0; p->previous_error=0;
}
float pid_update(pid_t *p, float target, float measured, float dt_s) {
    if (dt_s <= 0) return 0;
    float e = target - measured;
    p->integral += e * dt_s;
    float derivative = (e - p->previous_error) / dt_s;
    p->previous_error = e;
    return p->kp*e + p->ki*p->integral + p->kd*derivative;
}
