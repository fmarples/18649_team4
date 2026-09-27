#ifndef LAB2_BLINKER_CORE_H
#define LAB2_BLINKER_CORE_H

#include <stdbool.h>
#include <stdint.h>

#define BLINK_LEFT_BUTTON (1U << 5)
#define BLINK_RIGHT_BUTTON (1U << 4)
#define BLINK_TURN_RAW 8000
#define BLINK_RETURN_RAW 6000

enum blink_mode { BLINK_OFF, BLINK_LEFT, BLINK_RIGHT, BLINK_HAZARD };
struct blinker {
	enum blink_mode mode;
	uint32_t previous_buttons;
	uint64_t epoch_ms;
	bool crossed_turn;
	bool recovering;
};
struct blink_output { bool left, right; };

/* One owner calls these functions. Time must be monotonic milliseconds. */
void blinker_reset(struct blinker *b);
struct blink_output blinker_step(struct blinker *b, uint64_t now_ms,
	bool ready, bool fault, uint32_t buttons, int32_t steering_raw);
const char *blinker_mode_name(enum blink_mode mode);

#endif
