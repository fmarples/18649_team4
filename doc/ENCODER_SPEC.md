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

**Use the validated 1320 counts per wheel revolution for this chassis.**
The measurements differ from 1320 by about -0.08% and +0.53%, respectively.
The user has reconfirmed this calibration; do not request another hand-turn
measurement. Zero detected invalid transitions alone does not prove that no
edges were missed.

## Current decision: measure full-duty speed directly

On 2026-09-27, the user explicitly requested a powered **100% duty-cycle**
measurement using **1320 counts/revolution** and the encoder count change
across a measured time interval. Use MCU sample timestamps, exclude startup
and coast-down, and show the raw endpoints as well as each wheel's RPM and
their average:

`RPM = forward_count_delta * 60000 / (1320 * elapsed_ms)`

**After the measurement, the user selected 300 RPM at full throttle.**
The earlier claim that the user selected 85 RPM was incorrect. The chosen
pedal mapping uses the validated 1320 counts/revolution and a linear
300 RPM endpoint, with a low-pedal STOP region below the measured sustaining
speed. The initial cutoff is 23 RPM, about 7.67% pedal travel, from the existing
40%-duty measurements. See [the integrated motor-control policy](../PROTOCOL.md#motor-control).
The measured full-duty speed remains 316.59 RPM; it is not the mapping endpoint. Gearbox-based calculations and extrapolated speeds
have been removed. Continuous PID's existing
60% / 200 ms startup kick and 40..100% running PWM authority remain unchanged.
A bounded fixed-duty diagnostic measures speed independently of PID.

The requested trial subsequently completed. At 100% duty, over MCU time
9745..10646 ms (901 ms), forward count changes were **6285 left** and
**6266 right**: **317.07/316.11 RPM**, average **316.59 RPM**. Both outputs
were disabled and rest verified afterward. These values use 1320 directly;
see [raw endpoints and evidence](MOTOR_CHARACTERIZATION.md#full-duty-measurement-2026-09-27).

The abandoned ten-turn recheck obtained no serial data and produced no new
calibration result. Its failed captures are in
`logs/motor-bench/encoder-calibration-20260927-062012/` and
`encoder-calibration-20260927-062116/`, with `crash.txt` in each directory.

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
convert them to wheel RPM using 1320 counts/revolution. Continuous PID is
implemented in the standalone bench and connected to the root Pi-link app.
That integrated image is built/host-tested but not flashed or hardware-tested.

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

## Confirmed motor model and advertised speeds

The user identified the motors as **JGB37-520R30-12**, the highlighted 1:30
model in the [supplied specification image](assets/JGB37-520R30-12-spec.png).
It lists **280 RPM rated** and **320 RPM no-load** at **12 V**, with A/B
encoders, 11 magnetic-ring lines and a 3.3–5 V encoder supply. See the
[hardware record](HARDWARE.md#confirmed-motor-specifications) for the full table.

This supersedes the generic chassis listing's earlier 85 RPM rated / 110 RPM
no-load figures for the team's motors. Published speeds do not replace the
measured **316.59 RPM** full-duty average or the user-selected **300 RPM**
full-throttle target. Encoder-to-RPM calculations continue to use the team's
validated **1320 counts/revolution** and measured elapsed time.

## Team status and safety

The encoder-only app counts x4 on all A/B edges. Hand-turn testing confirmed that forward motion makes the left raw count decrease and the right raw count increase. Negate the left raw delta and retain the right raw delta before averaging velocities. The diagnostic firmware prints raw counts and MCU timestamps; the host holding-test script applies the provisional 1320 counts/rev calibration. Continuous PID is implemented in the standalone motor bench. Geometric circumference is now calculated from the reported 75 mm diameter; loaded rolling circumference and powered-speed accuracy remain unmeasured.

The [confirmed JGB37-520R30-12 specification](assets/JGB37-520R30-12-spec.png) lists **3.2 A stall current**. This exceeds the team's earlier **2 A per channel** L298N concern. Avoid a powered stall test until the driver and thermal limits have been evaluated.
