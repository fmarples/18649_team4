#ifndef DRIVE_CONTROL_H
#define DRIVE_CONTROL_H
void drive_control_init(void);
void drive_control_step(int16_t throttle, int16_t brake, int error_state);
#endif
