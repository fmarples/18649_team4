/* Exercise the real Lab 2 PID through the non-actuating Lab 3 workload. */
#include "pid_measurement.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    struct lab3_pid_measurement measurement;
    lab3_pid_measurement_init(&measurement);
    struct lab3_pid_result result = lab3_pid_measurement_step(&measurement);
    /* 44 counts in 20 ms at 1320/rev = 100 RPM; target 150.
     * P=6, I=60+0.35*50*0.02=60.35, D=0 => 66.35 percent. */
    assert(result.status == 0);
    assert(result.samples == 1);
    assert(result.rpm_milli == 100000);
    assert(result.duty_milli >= 66349 && result.duty_milli <= 66351);
    result = lab3_pid_measurement_step(&measurement);
    assert(result.samples == 2);
    assert(result.duty_milli >= 66699 && result.duty_milli <= 66701);
    bool high_limit = false, low_limit = false;
    for (unsigned i=2; i<900; ++i) {
        result = lab3_pid_measurement_step(&measurement);
        assert(result.status == 0);
        assert(result.samples == i+1);
        assert(result.duty_milli >= 40000 && result.duty_milli <= 100000);
        high_limit |= result.duty_milli == 100000;
        low_limit |= result.duty_milli == 40000;
    }
    assert(high_limit && low_limit);
    result = lab3_pid_measurement_step(&measurement);
    assert(result.samples == 901);
    assert(result.rpm_milli == 100000);
    assert(result.duty_milli >= 66349 && result.duty_milli <= 66351);
    puts("Lab 2 PID synthetic workload: changing output, both clamps, repeatability passed");
    return 0;
}
