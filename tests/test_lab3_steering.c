/* Verify the calibrated Lab 2 mapping through the measurement workload interface. */
#include "steering_measurement.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    assert(lab3_steering_pulse(-32768) == 1200);
    assert(lab3_steering_pulse(-16384) == 1400);
    assert(lab3_steering_pulse(0) == 1600);
    assert(lab3_steering_pulse(16384) == 1800);
    assert(lab3_steering_pulse(32767) == 2000);
    unsigned previous = 1200;
    for (int value=-32768; value<=32767; ++value) {
        unsigned pulse = lab3_steering_pulse((int16_t)value);
        assert(pulse >= previous && pulse >= 1200 && pulse <= 2000);
        previous = pulse;
    }
    puts("Lab 2 steering: calibrated endpoints, midpoints and monotonic full-range sweep passed");
    return 0;
}
