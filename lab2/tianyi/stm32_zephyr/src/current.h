#ifndef CURRENT_H
#define CURRENT_H

#include <stdint.h>

int current_init(void);
int current_get_mA(int32_t *left_mA,
                   int32_t *right_mA,
                   int32_t *servo_mA,
                   uint32_t *valid_mask);

#endif
