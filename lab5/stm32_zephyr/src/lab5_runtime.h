#ifndef LAB5_RUNTIME_H
#define LAB5_RUNTIME_H
#include <zephyr/drivers/can.h>
int lab5_runtime_init(unsigned id, void (*send)(unsigned, const struct can_frame *));
bool lab5_runtime_receive(unsigned bus, const struct can_frame *, uint64_t raw_us);
uint64_t lab5_raw_us(void);
uint64_t lab5_global_us(void);
bool lab5_error(void);
unsigned lab5_hazard_hz(void);
void lab5_pause(bool paused);
void lab5_ready(void);
#endif
