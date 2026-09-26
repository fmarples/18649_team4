#include "self_test.h"
#include "safety.h"

/* TODO: Replace with the button index selected by your team in Part 1. */
#define SELF_TEST_BUTTON 2

static uint32_t previous_buttons;

void self_test_init(void) { previous_buttons = 0; }

void self_test_update(uint32_t buttons) {
    bool pressed = (buttons & (1u << SELF_TEST_BUTTON)) &&
                   !(previous_buttons & (1u << SELF_TEST_BUTTON));
    if (pressed) {
        /* TODO: Implement your required single/double press behavior.
         * The checkoff calls for a single press to enter hazards + braking,
         * and a double press to return to normal. The exact debounce/timing
         * policy is a team design decision. */
        if (safety_in_error()) {
            safety_clear_error();
        } else {
            safety_enter_error();
        }
    }
    previous_buttons = buttons;
}
