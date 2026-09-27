#ifndef FAKE_PWM_H
#define FAKE_PWM_H
#include <stdbool.h>
#include <stdint.h>
struct pwm_dt_spec { int unused; };
#define DT_NODELABEL(x) 0
#define PWM_DT_SPEC_GET(x) {0}
#define PWM_USEC(x) ((x) * 1000U)
static inline bool pwm_is_ready_dt(const struct pwm_dt_spec *p) { (void)p; return true; }
extern uint32_t fake_pulse_ns;
extern int fake_pwm_error;
static inline int pwm_set_dt(const struct pwm_dt_spec *p, uint32_t period, uint32_t pulse)
{ (void)p; (void)period; if (fake_pwm_error) return fake_pwm_error; fake_pulse_ns = pulse; return 0; }
#endif
