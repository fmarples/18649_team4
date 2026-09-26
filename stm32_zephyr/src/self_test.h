#ifndef LAB2_SELF_TEST_H
#define LAB2_SELF_TEST_H
#include <stdbool.h>
#include <stdint.h>

#define SELF_TEST_BUTTON (1U << 0) /* G920 A */
#define SELF_TEST_DOUBLE_MS 400U
#define SELF_TEST_RELEASE_MS 20U
struct self_test {
	bool active, was_down, have_release, waiting_second;
	uint64_t release_ms, first_press_ms;
};
void self_test_reset(struct self_test *s);
/* Call only for accepted fresh commands; never from unvalidated input. */
void self_test_input(struct self_test *s, uint64_t now_ms, uint32_t buttons);
bool self_test_fault(const struct self_test *s, bool link_ok);
#endif
