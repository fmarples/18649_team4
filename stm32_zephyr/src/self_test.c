#include "self_test.h"

void self_test_reset(struct self_test *s)
{
	*s = (struct self_test){0};
}

void self_test_input(struct self_test *s, uint64_t now, uint32_t buttons)
{
	bool down = (buttons & SELF_TEST_BUTTON) != 0;
	if (!down) {
		if (s->was_down) {
			s->release_ms = now;
			s->have_release = true;
		}
		s->was_down = false;
		return;
	}
	if (s->was_down) { return; }
	s->was_down = true;
	if (s->have_release && now - s->release_ms < SELF_TEST_RELEASE_MS) {
		return; /* Reject a short release/bounce, not a held press. */
	}
	if (s->waiting_second && now - s->first_press_ms <= SELF_TEST_DOUBLE_MS) {
		s->active = false;
		s->waiting_second = false;
	} else {
		/* Enter failure immediately; never wait for the double-click window. */
		s->active = true;
		s->waiting_second = true;
		s->first_press_ms = now;
	}
}

bool self_test_fault(const struct self_test *s, bool link_ok)
{
	/* Clearing the manual latch can never override a real link fault. */
	return !link_ok || s->active;
}
