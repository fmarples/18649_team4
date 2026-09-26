#include "blinker.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>

/* TODO: Replace aliases with your four LED GPIOs. */
static const struct gpio_dt_spec fl = GPIO_DT_SPEC_GET(DT_ALIAS(blinker_fl), gpios);
static const struct gpio_dt_spec fr = GPIO_DT_SPEC_GET(DT_ALIAS(blinker_fr), gpios);
static const struct gpio_dt_spec rl = GPIO_DT_SPEC_GET(DT_ALIAS(blinker_rl), gpios);
static const struct gpio_dt_spec rr = GPIO_DT_SPEC_GET(DT_ALIAS(blinker_rr), gpios);

/* TODO: Replace with the button indices recorded in Part 1. */
#define LEFT_BUTTON 0
#define RIGHT_BUTTON 1
/* TODO: Use your team-defined steering turn threshold. */
#define TURN_THRESHOLD 30

static enum { OFF, LEFT, RIGHT } active = OFF;
static int crossed_threshold;
static int last_steering;
static uint32_t last_buttons;
static bool phase;
static int64_t last_toggle_ms;

static void outputs(bool left_on, bool right_on) {
    gpio_pin_set_dt(&fl, left_on); gpio_pin_set_dt(&rl, left_on);
    gpio_pin_set_dt(&fr, right_on); gpio_pin_set_dt(&rr, right_on);
}

void blinker_init(void) {
    gpio_pin_configure_dt(&fl, GPIO_OUTPUT_INACTIVE); gpio_pin_configure_dt(&fr, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure_dt(&rl, GPIO_OUTPUT_INACTIVE); gpio_pin_configure_dt(&rr, GPIO_OUTPUT_INACTIVE);
    outputs(false, false);
    last_toggle_ms = k_uptime_get();
}

void blinker_update(int16_t steering, uint32_t buttons, int error_state) {
    int64_t now = k_uptime_get();
    if (error_state) {
        /* Error state: all four flash at 2 Hz, 50% duty. */
        if (now - last_toggle_ms >= 250) { phase = !phase; last_toggle_ms = now; }
        outputs(phase, phase);
        return;
    }

    bool left_pressed = (buttons & (1u << LEFT_BUTTON)) && !(last_buttons & (1u << LEFT_BUTTON));
    bool right_pressed = (buttons & (1u << RIGHT_BUTTON)) && !(last_buttons & (1u << RIGHT_BUTTON));
    if (left_pressed) active = LEFT;
    if (right_pressed) active = RIGHT;
    if (left_pressed && right_pressed) active = OFF;

    /* Self-cancel: pass the turn threshold, then return back past it. */
    if (active == LEFT && steering < -TURN_THRESHOLD) crossed_threshold = 1;
    if (active == RIGHT && steering > TURN_THRESHOLD) crossed_threshold = 1;
    if (active == LEFT && crossed_threshold && steering >= -TURN_THRESHOLD) { active = OFF; crossed_threshold = 0; }
    if (active == RIGHT && crossed_threshold && steering <= TURN_THRESHOLD) { active = OFF; crossed_threshold = 0; }

    /* Normal blinkers: 1 Hz, 50% duty => toggle every 500 ms. */
    if (now - last_toggle_ms >= 500) { phase = !phase; last_toggle_ms = now; }
    outputs(active == LEFT && phase, active == RIGHT && phase);
    last_steering = steering;
    last_buttons = buttons;
}
