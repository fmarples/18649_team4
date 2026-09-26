#ifndef SAFETY_H
#define SAFETY_H
#include <stdbool.h>
void safety_init(void);
void safety_enter_error(void);
void safety_clear_error(void);
bool safety_in_error(void);
void safety_check_link(void);
void safety_note_valid_command(void);
#endif
