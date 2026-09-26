/* Public PID behavior: measured dt/CPR, user-selected running floor and full PWM. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "velocity_control.h"

static void near(float actual, float expected)
{
    assert(fabsf(actual - expected) < 0.002f);
}

int main(void)
{
    struct velocity_control c;
    velocity_init(&c, -100, 200, 1000);
    assert(velocity_update(&c, -166, 266, 1050, 60, true) == 0);
    near(c.rpm[0], 60);
    near(c.rpm[1], 60);
    near(c.average_rpm, 60);
    near(c.command[0], 60); /* Integral starts at the existing startup duty. */
    near(c.command[1], 60);

    velocity_init(&c, 0, 0, 0);
    assert(velocity_update(&c, -44, 44, 50, 45, true) == 0);
    near(c.p_term, 0.6f);
    near(c.i_term, 60.0875f);
    near(c.command[0], 60.6875f);
    assert(velocity_update(&c, -110, 110, 100, 45, true) == 0);
    near(c.d_term, -0.5454545f);
    assert(c.p_term < 0);

    velocity_init(&c, 0, 0, 0);
    for (int64_t now = 50; now <= 1000; now += 50) {
        assert(velocity_update(&c, 0, 0, now, 1000, true) == 0);
        near(c.command[0], 100);
        near(c.command[1], 100);
        near(c.i_term, 60); /* No windup past available PWM. */
    }
    velocity_init(&c, 0, 0, 0);
    assert(velocity_update(&c, -33, 66, 50, 45, true) == 0);
    near(c.average_rpm, 45);
    near(c.command[0], 60);
    near(c.command[1], 60); /* Plain average-speed PID, no balancing/feedforward. */

    velocity_init(&c, 0, 0, 0);
    assert(velocity_update(&c, -660, 660, 50, 30, true) == 0);
    near(c.command[0], 40); /* User-requested sustaining floor while running. */
    near(c.command[1], 40);
    near(c.i_term, 60);

    velocity_init(&c, 0, 0, 0);
    assert(velocity_update(&c, -66, 66, 50, 60, false) == 0);
    near(c.i_term, 60);
    near(c.command[0], 0); /* Caller owns the 60% startup kick. */
    assert(velocity_update(&c, -132, 132, 100, 60, true) == 0);
    assert(velocity_update(&c, -198, 198, 150, 90, true) == 0);
    near(c.d_term, 0); /* Target alone produces no derivative kick. */
    assert(velocity_update(&c, -199, 199, 151, 90, true) == 0);
    assert(c.sample_ms == 150);
    assert(velocity_update(&c, -396, 396, 300, 90, true) == 0); /* No invented 100ms cutoff. */
    near(c.rpm[0], 60);
    assert(velocity_update(&c, 0, 0, 350, NAN, true) == -1);
    near(c.command[0], 0);
    assert(velocity_update(&c, 0, 0, -1, 45, true) == -1);
    puts("PASS: plain PID; actual time/calibration; 40..100% running duty; physical saturation anti-windup; invalid data fails off");
    return 0;
}
