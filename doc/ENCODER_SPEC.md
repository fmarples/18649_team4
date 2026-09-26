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
The standalone bench now transmits MCU-timestamped raw counts. Host diagnostics
convert them to wheel RPM using the provisional 1320 count calibration; no
closed-loop velocity feature or Part 2 integration has been added.

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

## Minimum tested startup duty

The **simultaneous** operating-case results now take precedence. At the user's
request, both motors were retested together at 10 kHz, wheels raised: 55% starts
passed 3/3, 50% failed; after a 60% / 200 ms kick, 40% holds passed three 4-second
trials, while 35% caused left no-progress cutoff and stopped both. These are
lowest tested passing values, not exact or loaded-operation minima. See
[Motor characterization](MOTOR_CHARACTERIZATION.md) for the per-wheel/average RPM
table, raw capture paths, final flashed profile and automated reset authorization.
Speed estimates use MCU-time deltas only during the late powered HOLD stage,
excluding kick and coast-down. They use the calibration and sign corrections above.

Earlier separate-wheel startup evidence follows; do not pool it with simultaneous
repeat counts.

The subsequent [startup sweep](../bringup/motor_test/README.md#startup-sweep-2026-09-27)
tested each motor separately, forward from rest, with raised wheels, the team's
12 V / 2 A supply, 10 kHz enable PWM and a maximum 200 ms pulse. The firmware
retained its 150 ms no-progress guard.

| Duty | Left | Right |
|---|---|---|
| 50% | Failed to start, 0/1 | Failed to start, 0/1 |
| 55% | Started, 3/3 | Started, 3/3 |
| 60% | Started, 1/1 | Started, 1/1 |

**55% is the lowest tested successful kickstart duty**, not an exact or universal
minimum. Duties 51–54% were not tested. The provisional bench kick setting is
60% with a 200 ms cap to provide margin above the tested passing duty. These
results do not establish the minimum duty needed to keep an already-moving
motor running, a throttle-to-speed mapping, or reliable ground-loaded or
simultaneous startup. Current and thermal limits remain unverified.

Encoder counts establish movement here, not a calibrated powered speed. Use the
provisional 1320 counts/wheel revolution above when converting count deltas;
do not treat coast-down counts as motion during the commanded pulse. The sweep
record links the persistent captures under `logs/motor-bench/`. The
[hardware BOM](HARDWARE.md) records both the encoder calibration and startup duty.

## Product-page nominal value (does not match this bench result)

Hiwonder's [product listing](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503) and [Shopify product data](https://www.hiwonder.com/products/ackermann-steering-chassis.js) specify a **1:90 gear ratio** and **11 magnetic poles** for the chassis motor. The [STM32 tutorial](https://docs.hiwonder.com/projects/Ackermann-Chassis/en/latest/docs/2_STM32_Version_checked.html) says the motor shaft produces 11 pulses per revolution and the timer counts every rising and falling edge of phases A and B, giving x4 quadrature decoding. Its sample defines `MOTOR_JGB520_TICKS_PER_CIRCLE` as `3960.0f`.

Combining those values gives the nominal count:

`11 pulses/motor revolution * 4 counts/pulse * 90 motor revolutions/output revolution = 3960 counts/output revolution`

Those specifications predict **3960 counts per gearbox-output revolution**, and 3960 counts per wheel revolution if the wheel is directly driven by that output. This was the original expectation, but the actual chassis measurements above do not support it.

## Source conflict

The same [STM32 tutorial](https://docs.hiwonder.com/projects/Ackermann-Chassis/en/latest/docs/2_STM32_Version_checked.html) contains a contradictory paragraph that calls the ratio 45:1, calculates with 30:1, reports 1320 pulses per revolution, and then says the counter increases by 3960. That paragraph conflicts internally and with the tutorial's 90:1 code comment and `3960.0f` constant. The prose alone cannot resolve which motor variant is installed. The independent bench measurements above support approximately 1320 for this particular chassis.

## Team status and safety

The encoder-only app counts x4 on all A/B edges. Hand-turn testing confirmed that forward motion makes the left raw count decrease and the right raw count increase. Negate the left raw delta and retain the right raw delta before averaging velocities. The diagnostic firmware prints raw counts and MCU timestamps; the host holding-test script applies the provisional 1320 counts/rev calibration. No closed-loop speed control has been implemented. Geometric circumference is now calculated from the reported 75 mm diameter; loaded rolling circumference and powered-speed accuracy remain unmeasured. Using 3960 instead of 1320 would underestimate wheel speed by about a factor of three.

The [product listing](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503) specifies **3.2 A stall current**. This exceeds the team's earlier **2 A per channel** L298N concern. Avoid a powered stall test until the driver and thermal limits have been evaluated.
