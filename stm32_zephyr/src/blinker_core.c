#include "blinker_core.h"

void blinker_reset(struct blinker *b)
{
	*b = (struct blinker){0};
}

static void select_mode(struct blinker *b, enum blink_mode mode, uint64_t now)
{
	b->mode = mode;
	b->epoch_ms = now;
	b->crossed_turn = false;
}

struct blink_output blinker_step(struct blinker *b, uint64_t now,
	bool ready, bool fault, uint32_t buttons, int32_t steer)
{
	uint32_t mask = BLINK_LEFT_BUTTON | BLINK_RIGHT_BUTTON;
	buttons &= mask;
	uint32_t pressed = buttons & ~b->previous_buttons;
	b->previous_buttons = buttons;

	if (fault) {
		if (b->mode != BLINK_HAZARD) {
			select_mode(b, BLINK_HAZARD, now);
		}
		b->recovering = true;
	} else if (!ready) {
		select_mode(b, BLINK_OFF, now);
	} else if (b->recovering) {
		/* A held paddle on recovery is not a new turn request. */
		select_mode(b, BLINK_OFF, now);
		b->recovering = false;
	} else {
		if (pressed == mask) {
			/* Two new presses in one frame cancel. Otherwise newest press wins. */
			select_mode(b, BLINK_OFF, now);
		} else if (pressed & BLINK_LEFT_BUTTON) {
			select_mode(b, b->mode == BLINK_LEFT ? BLINK_OFF : BLINK_LEFT, now);
		} else if (pressed & BLINK_RIGHT_BUTTON) {
			select_mode(b, b->mode == BLINK_RIGHT ? BLINK_OFF : BLINK_RIGHT, now);
		}

		if (b->mode == BLINK_LEFT) {
			if (steer <= -BLINK_TURN_RAW) { b->crossed_turn = true; }
			if (b->crossed_turn && steer >= -BLINK_RETURN_RAW) {
				select_mode(b, BLINK_OFF, now);
			}
		} else if (b->mode == BLINK_RIGHT) {
			if (steer >= BLINK_TURN_RAW) { b->crossed_turn = true; }
			if (b->crossed_turn && steer <= BLINK_RETURN_RAW) {
				select_mode(b, BLINK_OFF, now);
			}
		}
	}

	/* Absolute phase: late calls do not shift subsequent blink deadlines. */
	uint64_t half_period = b->mode == BLINK_HAZARD ? 250U : 500U;
	bool on = ((now - b->epoch_ms) / half_period) % 2U == 0;
	return (struct blink_output){
		.left = on && (b->mode == BLINK_LEFT || b->mode == BLINK_HAZARD),
		.right = on && (b->mode == BLINK_RIGHT || b->mode == BLINK_HAZARD),
	};
}

const char *blinker_mode_name(enum blink_mode mode)
{
	switch (mode) {
	case BLINK_LEFT: return "LEFT";
	case BLINK_RIGHT: return "RIGHT";
	case BLINK_HAZARD: return "HAZARD";
	default: return "OFF";
	}
}
