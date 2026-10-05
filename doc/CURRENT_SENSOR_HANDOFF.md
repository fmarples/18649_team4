# Part 3.5 current sensing

## Implemented scope and user decision

The integrated `stm32_zephyr/` application now reads all three Makerfabs ACS712
5A modules through ADC1 and reports signed milliamps in the existing status
frame. The user selected **direct sensor-to-ADC connections, no divider**, and
**+4320 mA when the positive measurement range is exceeded**. This supersedes
the earlier divider proposal. Sensor power remains 5 V; the ADC reference
remains nominally 3.3 V. Current sensing is read-only, with no motor cutoff,
stall timer, servo trip or change to the existing actuator policies.

All three channels now have recorded live acquisition. The September 28 bench
session supplies rest/motor-running readings and a right-wheel obstruction
attempt; see the bench record below. Measured calibration, each sensor's complete
rest/running/stall set, PWM noise characterization and acquisition timing still
need verification. Part 3.5 is not yet recorded as complete.

### Three-sensor preparation, 2026-09-28

The user now has the third sensor and confirmed it is also ACS712-05B / 5 A.
The stability branch defaults to channel mask 7 (left/A0, right/A1, servo/A3)
and shows all three channels in the Windows chart. The user subsequently
reported the third sensor connected and the system powered again, with correct
voltages (exact meter values not supplied). The mask-7 image was then flashed:
77 complete idle USB snapshots showed all three valid, ADC error 0 and age
2 ms. Right readings were 529–730 mA using nominal conversion; calibration is
still pending. See [stability verification](ACTUATOR_STABILITY.md). Before this change,
the supervised stability tests used mask 5 and acquired the two connected
left/servo sensors; they did not use the pre-current-sensing firmware.

The right sensor belongs in the OUT3-to-right-motor lead. Its signal OUT is
PA1/A1, VCC uses the HW-688 5 V rail, and GND joins the common signal ground.
Nominal right conversion remains 2500 mV zero / 185 mV per amp. These constants
do not substitute for measuring that sensor's zero offset. Firmware inverts
the converted signs for both motor channels, as requested after their sensor
polarities were found to be reversed; servo polarity is unchanged. This is a
software sign correction, not a wiring-orientation change.
No actuator policy, ADC filtering, status format or acquisition priority changed.
`diagnostics/two_sensors.conf` retains the earlier mask-5 configuration; its
matching Windows selection is `--current-channels left servo`.

## Electrical and conversion contract

| Channel order | Sensor output | Nucleo header | ADC1 channel |
|---|---|---|---|
| 0 | Left motor | A0 / PA0 | 0 |
| 1 | Right motor | A1 / PA1 | 1 |
| 2 | Servo | A3 / PB0 | 8 |

Keep signal ground common. Use the module's 5 V supply, not the encoder's
3V3 rail. These are planned connections, not confirmation of installed wiring.
The high-current terminals go in series with the measured circuit; their
orientation determines the sign. Neither firmware nor ADC saturation limits
voltage physically. Verify supply and signal levels, including power sequencing,
before applying this wiring plan.

Sources:

- [Makerfabs MSE71205A](https://www.makerfabs.com/acs712-current-sensor-5a.html):
  -5 to +5 A, 5 V supply, nominal 2.5 V at zero, 185 mV/A.
- [ST DS10086 Rev 4](https://download.mikroe.com/documents/datasheets/erp/STM32F401RE.pdf),
  Table 11 and note 2: 4.0 V absolute maximum for analog use. This is a stress
  rating, not the ADC conversion range or a guarantee of continuous operation.
  Table 66: conversion range 0 to VREF+, nominally 3.3 V here.
- [Lab 2 handout](18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf),
  Part 3.5: read all three into status, read-only, then record bench results.

At nominal values, +5 A produces 3.425 V, above the measurable range but below
the published absolute maximum. The positive conversion endpoint is
`(3.3 - 2.5) / 0.185 = 4.3243 A`. The user selected a rounded reporting ceiling
of **4.320 A**. The -5 A endpoint is 1.575 V and does not clip the ADC.

ADC resolution is 12 bits. Firmware uses `raw * reference_mV / 4096` and
`current_mA = (output_mV - zero_mV) * 1000 / sensitivity_mV_per_A`, retaining
microvolt precision until final signed rounding. Nominally one LSB is
`3300 / 4096 = 0.805664 mV`, or **4.355 mA**. Left and right motor values are
then negated; servo values retain the sensor's measured sign. Negative current
is preserved.

Per-channel Kconfig values in `stm32_zephyr/Kconfig` are initially vendor
nominal, not measured calibration:

- `CONFIG_LAB_CURRENT_{LEFT,RIGHT,SERVO}_ZERO_MV=2500`
- `CONFIG_LAB_CURRENT_{LEFT,RIGHT,SERVO}_SENSITIVITY=185`, in mV/A
- ADC reference: `&adc1 { vref-mv = <3300>; };` in `stm32_zephyr/app.overlay`

Measure each zero-current output and reference rail before replacing these
values. Use a known current and voltage change to refine sensitivity, then
rebuild. There is no automatic boot zeroing, because a connected motor or
servo may already draw current at boot.

## Acquisition, filtering and status

`current_backend_read()` configures ADC1 channels 0, 1 and 8 once, then makes
three single-channel reads per work item, each containing eight samples. The
STM32 non-DMA driver starts each repeat only after consuming the prior sample.
This avoids the multi-channel overrun/completion hang demonstrated in the
[ADC diagnostic record](CURRENT_ADC_DIAGNOSIS.md). ADC clock is 84 MHz / 4 = 21 MHz; each
channel uses 480 acquisition cycles, 12-bit resolution and no hardware
oversampling. A batch mean reduces noise without carrying old readings across
work periods. Nominal conversion time for 24 readings is about 0.56 ms,
excluding driver/interrupt/scheduler overhead; this is not measured latency.
Filtering cannot recover peaks clipped by the ADC or guarantee rejection of
PWM-correlated noise.

If any sample for a channel reaches code 4095, the whole batch reports +4320 mA
for that channel rather than averaging away the clip. Converted values above
4320 also cap there. Treat **4320 as a ceiling indication, not an exact current**.
The Pi console labels it `4320mA[CEILING]`; CSV and wire values remain numeric.
There is no new saturation bit or protocol version.

| Item | Contract |
|---|---|
| Backend API | `int current_backend_read(int32_t ma[3], uint32_t *valid_mask)` |
| Channel order | Left motor, right motor, servo |
| Validity | Acquired and converted with configured constants; not proof of sensor connection or measured calibration |
| Real zero | `0` with its validity bit set |
| Acquisition/setup error | Negative errno; all channels `INT32_MIN`, validity zero |
| Retry | Next work item retries setup/read; no fabricated zero or last-good replacement |
| Period / priority | Existing 20 ms dedicated priority-3 workqueue |
| Timestamp | Before acquisition, so conversion/filter time counts toward age |
| Stale data | Validity clears at 100 ms; unavailable fields become `INT32_MIN` |
| Status path | Priority 2 copies a short mutex-protected snapshot; it never waits for ADC |
| Control path | No current values or ADC errors affect actuators |

An unconnected analog input can float to a plausible voltage. A successful ADC
read cannot prove a module is connected. A disconnected motor with a still
connected sensor should be distinguished experimentally from stall/load current;
no disconnect or stall classifier is implemented.

USB diagnostics now include a `CURRENT` line every approximately 250 ms:

```text
CURRENT left_ma=... right_ma=... servo_ma=... valid=7 age_ms=... error=0
```

`error` is the acquisition errno, not an actuator fault. The binary status
remains 56 bytes; current fields are at offsets 32/36/40 and validity at 44.
See [PROTOCOL.md](../PROTOCOL.md).

## Build, tests and persistent evidence

On this Windows host, build without flashing:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\build_part4.ps1 -ZephyrWorkspace C:\Users\13982\zephyrproject -Sdk C:\Users\13982\zephyr-sdk-0.17.4
python -m unittest discover -s tests -p 'test_*.py' -v
python test_protocol.py -v
```

Software checks for this change:

- NUCLEO-F401RE build, Zephyr v4.3.0 / SDK 0.17.4: passed.
- Generated ADC pins, channels, /4 clock and existing actuator allocations: passed.
- Python discovery including native production-C current, servo and motor tests:
  45 passed.
- Protocol suite including signed currents, zero, saturation display and CRC: 10 passed.
- The current backend test substitutes only ADC hardware with synthetic raw codes.
  It covers channel order, signed conversion, batch filtering, clipping, setup/read
  errors, recovery and cache expiry. No physical end-to-end result is claimed.
- Existing QEMU cache tests were updated to remove the obsolete ENOSYS backend
  expectation. QEMU was not rerun on this host, which has no QEMU executable.

The earlier image was SHA-256
`5ddeafc5992a8c8cdda168164524020d3add0fd44ee09199823e18f95e88f5a7`.
On 2026-09-28, authorized current-only diagnosis replaced it with the
single-channel acquisition fix. Final `build/part4/zephyr/zephyr.bin` SHA-256:
`eb46d9cf7c2ab5e5d3a50b768c70a7b0becd76180772ecc8887aeabcd8e3e924`.
A passive boot capture contains 243 fresh, valid samples over 62.8 seconds with
no commanded movement. The managed wheel session was stopped for that capture;
a later live-session check passed after the user corrected sensor grounding. See the
[diagnostic record](CURRENT_ADC_DIAGNOSIS.md) for the controlled overrun evidence,
external driver restoration, logs and limits of the result.
Build and verification logs are in
`logs/current-sense/`: `build.log`, `generated-check.log`, `host-0.log`,
`host-1.log`, `python-tests.log`, `protocol-tests.log`. Verification exceptions
use `verify.crash.txt` when produced.

For hardware evidence, capture the complete ST-LINK console to
`logs/current-sense/console-<timestamp>.log` and Pi status CSV to
`logs/current-sense/status-<timestamp>.csv`. The existing Windows servo console
supports `--port <rediscovered COM port> --log <new log path>` and records all
lines, including CURRENT and Zephyr fatal traces. It sends servo OFF on entry
and exit, so use it only when that action is intended. Pi bridge `--log` preserves
every received status frame. No native MCU crash dump is configured; the full
USB capture is the persistent MCU fatal-report evidence. Retain the matching
`zephyr.elf` for symbol lookup. Never assume the previous COM port or board drive.

## Hardware observations and grounding correction

The first flashed run of this backend reported **about -8 A on all three channels,
with validity bits set**, at rest and with no load. That is a real acquisition
result, but not an accepted current measurement. Plausible causes include
unconnected/floating ADC inputs, an unpowered sensor, a wrong module output pin,
or a zero offset far from the assumed 2.5 V. Until wiring and offsets are checked,
treat these numbers as evidence that the ADC path runs, not that it measures.
No user-visible alarm or actuator action depends on them.

After the acquisition fix, the final passive capture reported left and servo
at +4320 mA throughout, and right at -6131 to -4908 mA. These remain implausible
unvalidated readings, not calibrated rest currents. The diagnostic scan image
had reported substantially different values. Check the actual sensor outputs,
supply, ground and ADC connection with a meter before interpreting the numbers.
No zeros, offsets, sign changes or ceiling changes were introduced to hide them.

The user subsequently confirmed only A0 and A3 are connected, identified missing
sensor grounds, and reported connecting them. Before grounding, OUT measured
3.824 V and 3.695 V relative to Nucleo GND, an invalid reference for ungrounded
modules. After correction, an eight-second passive capture under LINK_OK showed
31 fresh samples, error 0, age 2..20 ms; clipping disappeared. A0 averaged
680.1 mA, range 577..782; A3 averaged 899.1 mA, range 814..1047, under the
unchanged nominal conversion. These still need measured zero offsets/reference
and a known-current check. A1 is physically unconnected; its negative numeric
readings are not meaningful current even though ADC acquisition succeeds.

The live Pi CSV and GUI sample-file checks now pass. The original ADC hang and
the missing sensor grounds were separate issues. Full details and persistent
artifacts are in [ADC diagnosis](CURRENT_ADC_DIAGNOSIS.md). The user's new live
session was preserved. Final combined software suite: 63 host tests and 10
protocol tests passed.

## Remaining Part 3.5 bench record

Verify wiring and common ground with power off before changes. Confirm sensor
supply, zero offsets, reference rail and polarity first. Then record each sensor
at rest, running and briefly stalled, including noise/min/max and any clipping.
The handout limits a stall to one or two seconds; this software does not enforce
that duration or limit current. The shared 2 A supply and L298N current/thermal
margins are still unverified. On September 28 the user reported multiple
sub-second obstruction attempts near the end of a recorded session, tentatively
identifying the right wheel. The recordings below support that identification;
they do not establish an exact mechanical stall duration.

| Sensor | Rest reported mA | Running reported mA | Brief obstruction reported mA | Capture / notes |
|---|---|---|---|---|
| Left motor | +735.5 median | +617 median | Not identified | Motor encoder near 300 RPM in running window |
| Right motor | +700 median | +588.5 median | -1166 captured minimum | Right encoder nearly stopped during the final obstruction attempt |
| Servo | +686 median, holding | Not identified | Not identified | +678.5 median while motors ran is not a servo-motion measurement |

These are **nominally converted readings**, not calibrated physical currents.
They were captured before the motor-channel polarity correction above; invert
the left and right signs only to compare with corrected firmware reports.
Rest window: 2026-09-28 15:21:25–15:21:33 EDT (400 status frames); motor-running
window: 15:21:39–15:21:44 (250 frames). The final attempt window is
15:22:24–15:22:26.35 (117 frames); its right-channel minimum occurred at about
15:22:25.80. Wall times are approximate, obtained by aligning the laptop receive
timestamps and MCU uptime. The firmware and conversion constants were unchanged.

At about 15:22:25.55 / 15:22:25.80, right speed was 9.957 / 3.827 RPM while left
speed was 237.420 / 261.302 RPM. Requested speed was 179.295 RPM; common motor
duty rose to 85.403% / 88.524%. The implemented controller regulates average
wheel speed, so increased drive to the unrestrained wheel is consistent with
that policy. The USB snapshots are about 250 ms apart; the 20 ms status frames
carry current but not encoder speed. Neither proves a precise zero-speed stall
duration or instantaneous electrical peak.

The motor rest offsets and negative-going load response in the historical
capture require zero and reference calibration before adopting physical current
thresholds. Motor-channel signs are now inverted in firmware per the user's
polarity correction; no physical current threshold is used.
Do not silently subtract these rest values or use absolute values: a holding
servo can draw real current, and the selected rest is not a verified zero-current
calibration. The right minimum is a captured extreme, not a stall average.

All 4650 complete USB diagnostic groups in the 20-minute capture reported
valid mask 7, ADC error 0 and sample age 1–21 ms. All 40,952 GUI status frames
had numeric currents below the +4320 mA ceiling. During the final attempt,
all status states were LINK_OK, rejection count stayed 5387 and USB timeout
count stayed 18. A separate timeout around 15:21:37.6 means this is not a clean
communication-stability run. The rejection total came from the earlier
bad-input exercise; do not attribute it to the obstruction attempt.

Source captures (retained locally, not committed):

- `usb-20260928-150433.log`, SHA-256
  `3eaf7ea407acb0762f479565882afc45c2b7195fb561f5df99ee01568d28633b`.
- `20260928-150258-512531-45420.frames.jsonl`, SHA-256
  `a1772c5c7fae0d26de3a4909e392ae96e6e285ba32c6af9a10b1c0886ae56210`.

The local analysis report and standalone chart preserve all signs and nominal
offsets. No firmware, wiring or calibration changes were made for this analysis.

Measure acquisition time, noise with motor PWM active and the 20 ms status
cadence under combined load. Do not fill this table from nominal component
ratings or synthetic tests.
