#include "safety.h"
#include "motor.h"
#include "blinker.h"
#include <zephyr/kernel.h>

/* The handout says 150 ms for three missed command updates. The checkoff says
 * fail-safe within 100 ms. This starter uses 100 ms; document your team's choice. */
#define LINK_TIMEOUT_MS 100
static bool error_state = true;
static int64_t last_valid_command_ms;

void safety_init(void) { error_state = true; last_valid_command_ms = k_uptime_get(); }
void safety_enter_error(void) { error_state = true; motor_dynamic_brake(); }
void safety_clear_error(void) { error_state = false; }
bool safety_in_error(void) { return error_state; }
void safety_check_link(void) {
    if (k_uptime_get() - last_valid_command_ms >= LINK_TIMEOUT_MS) safety_enter_error();
}
/* TODO: Call this whenever the UART parser accepts a VALID command. */
void safety_note_valid_command(void) { last_valid_command_ms = k_uptime_get(); }
