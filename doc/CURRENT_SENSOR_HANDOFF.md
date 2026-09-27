# Part 3.5 current sensing

## Implemented scope and user decision

The integrated `stm32_zephyr/` application now reads all three Makerfabs ACS712
5A modules through ADC1 and reports signed milliamps in the existing status
frame. The user selected **direct sensor-to-ADC connections, no divider**, and
**+4320 mA when the positive measurement range is exceeded**. This supersedes
the earlier divider proposal. Sensor power remains 5 V; the ADC reference
remains nominally 3.3 V. Current sensing is read-only, with no motor cutoff,
stall timer, servo trip or change to the existing actuator policies.

This is software implementation, not hardware completion of Part 3.5. Wiring,
calibration, PWM noise, acquisition timing and the rest/running/stall readings
remain unverified.

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
`3300 / 4096 = 0.805664 mV`, or **4.355 mA**. Negative current is preserved.

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

`current_backend_read()` configures ADC1 channels 0, 1 and 8 once, then reads
eight complete scans per work item. ADC clock is 84 MHz / 4 = 21 MHz; each
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

Firmware: `build/part4/zephyr/zephyr.bin`. This build is **byte-identical**
(SHA-256 `5ddeafc5992a8c8cdda168164524020d3add0fd44ee09199823e18f95e88f5a7`)
to the image the user authorized flashing for the steering task, so the ADC
backend is already running on that Nucleo; no separate sensor flash is pending.
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

## Observed hardware reading, not yet explained

The first flashed run of this backend reported **about -8 A on all three channels,
with validity bits set**, at rest and with no load. That is a real acquisition
result, but not an accepted current measurement. Plausible causes include
unconnected/floating ADC inputs, an unpowered sensor, a wrong module output pin,
or a zero offset far from the assumed 2.5 V. Until wiring and offsets are checked,
treat these numbers as evidence that the ADC path runs, not that it measures.
No user-visible alarm or actuator action depends on them.

## Remaining Part 3.5 bench record

Verify wiring and common ground with power off before changes. Confirm sensor
supply, zero offsets, reference rail and polarity first. Then record each sensor
at rest, running and briefly stalled, including noise/min/max and any clipping.
The handout limits a stall to one or two seconds; this software does not enforce
that duration or limit current. The shared 2 A supply and L298N current/thermal
margins are still unverified. No stall test was performed or authorized here.

| Sensor | Rest mA | Running mA | Brief stall mA | Capture / notes |
|---|---|---|---|---|
| Left motor | Pending | Pending | Pending | First run reported about -8 A at rest; see the note above |
| Right motor | Pending | Pending | Pending | First run reported about -8 A at rest; see the note above |
| Servo | Pending | Pending | Pending | First run reported about -8 A at rest; see the note above |

Measure acquisition time, noise with motor PWM active and the 20 ms status
cadence under combined load. Do not fill this table from nominal component
ratings or synthetic tests.
