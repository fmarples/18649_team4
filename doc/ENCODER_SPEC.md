# Hiwonder wheel encoder count — specification and bench measurements

## Bench result takes precedence

With the team's actual chassis, x4 encoder-test firmware, and 12 V supply off,
the user hand-turned each marked wheel exactly one vehicle-forward revolution:

| Wheel | Starting raw count | Ending raw count | Signed delta | Absolute counts / turn |
|---|---:|---:|---:|---:|
| Left | -37 | -1356 | -1319 | 1319 |
| Right | -67 | 1260 | +1327 | 1327 |

The other wheel's count remained unchanged in each measurement. Both invalid
transition counters and GPIO error counters remained zero. The user determined
one revolution by aligning a tire mark with a fixed reference.

**Use 1320 counts per wheel revolution as the provisional x4 calibration for
this chassis, not 3960.** The measurements differ from 1320 by about -0.08% and
+0.53%, respectively; manual endpoint alignment is a plausible explanation,
not a proven cause. Repeat over several revolutions before treating 1320 as a
precision calibration. Zero detected invalid transitions alone does not prove
that no edges were missed.

The result is consistent with `11 * 4 * 30 = 1320` and therefore suggests a
30:1 gearbox if the documented 11 pulses/motor revolution applies. Gearbox ratio
and motor model have not been independently verified from the physical label.

## Wheel size and optional linear-velocity conversion

The user reports an outside wheel diameter of **75 mm**. Treat this as the
reported physical measurement; loaded rolling circumference has not been measured.

- Diameter: `D = 0.075 m`.
- Geometric circumference: `C = pi * D = 0.235619 m` (about 235.6 mm).
- With provisional x4 calibration `N = 1320`, distance per count is
  `C / N = 0.0001784996 m` (about 0.1785 mm).
- Over elapsed time `dt` in seconds, each wheel's peripheral velocity is
  `v = corrected_count_delta * C / (N * dt)` in m/s.
- Correct raw deltas first: negate left, retain right; then average the two
  wheel velocities for control. This is an encoder-based estimate, not a
  slip-compensated measurement of actual ground travel.

[Handout section 3.1](18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf)
requires a documented monotonic throttle-to-target-wheel-velocity mapping,
closed-loop encoder feedback, a chosen/documented maximum velocity, and control
using the average of the two encoder velocities. It does **not** require an
odometer or prescribe m/s as the unit. RPM/RPS control is also an option if the
units and mapping are documented consistently; wheel diameter is not needed for
that option. Circumference is useful if the team chooses linear velocity in m/s.
No velocity feature or calibration constants have been added to firmware yet.

## Powered motion and motor polarity

The separate `bringup/motor_test` app now uses the same x4 decoder and encoder
pins. Individual 100% / 200 ms kicks established that IN1=1/IN2=0 moves the left
wheel backward (positive raw left counts, also visually confirmed), while
IN3=1/IN4=0 moves the right wheel forward (positive raw right counts). The other
encoder remained unchanged in each test; no invalid transitions or GPIO errors
were reported. Wheels continued coasting after enable went low.

With left direction reversed to IN1=0/IN2=1, **one simultaneous 100% / nominal
5-second forward trial passed**. Left counts decreased and right counts increased
throughout the powered interval; no invalid transitions, GPIO errors or firmware
faults were reported. Both outputs then returned to disabled. Total deltas over
the run plus initial coast capture were left -37257 and right +38590; these totals
are **not** counts during exactly 5 powered seconds or a calibrated speed result.
See the [motor-test record](../bringup/motor_test/README.md) for the capture,
software motion guards, later scheduling correction and remaining limits.

## Product-page nominal value (does not match this bench result)

Hiwonder's [product listing](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503) and [Shopify product data](https://www.hiwonder.com/products/ackermann-steering-chassis.js) specify a **1:90 gear ratio** and **11 magnetic poles** for the chassis motor. The [STM32 tutorial](https://docs.hiwonder.com/projects/Ackermann-Chassis/en/latest/docs/2_STM32_Version_checked.html) says the motor shaft produces 11 pulses per revolution and the timer counts every rising and falling edge of phases A and B, giving x4 quadrature decoding. Its sample defines `MOTOR_JGB520_TICKS_PER_CIRCLE` as `3960.0f`.

Combining those values gives the nominal count:

`11 pulses/motor revolution * 4 counts/pulse * 90 motor revolutions/output revolution = 3960 counts/output revolution`

Those specifications predict **3960 counts per gearbox-output revolution**, and 3960 counts per wheel revolution if the wheel is directly driven by that output. This was the original expectation, but the actual chassis measurements above do not support it.

## Source conflict

The same [STM32 tutorial](https://docs.hiwonder.com/projects/Ackermann-Chassis/en/latest/docs/2_STM32_Version_checked.html) contains a contradictory paragraph that calls the ratio 45:1, calculates with 30:1, reports 1320 pulses per revolution, and then says the counter increases by 3960. That paragraph conflicts internally and with the tutorial's 90:1 code comment and `3960.0f` constant. The prose alone cannot resolve which motor variant is installed. The independent bench measurements above support approximately 1320 for this particular chassis.

## Team status and safety

The encoder-only app counts x4 on all A/B edges. Hand-turn testing confirmed that forward motion makes the left raw count decrease and the right raw count increase. Negate the left raw delta and retain the right raw delta before averaging velocities. The diagnostic firmware still prints raw counts; no velocity calibration constant has been applied to it. Geometric circumference is now calculated from the reported 75 mm diameter; loaded rolling circumference and powered-speed accuracy remain unmeasured. Using 3960 instead of 1320 would underestimate wheel speed by about a factor of three.

The [product listing](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503) specifies **3.2 A stall current**. This exceeds the team's earlier **2 A per channel** L298N concern. Avoid a powered stall test until the driver and thermal limits have been evaluated.
