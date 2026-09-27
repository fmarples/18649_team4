# Part 4 preparation: software evidence and remaining hardware work

**Part 3.5 update:** ADC acquisition has since replaced the unavailable backend.
The new NUCLEO build and generated-pin checks pass; 45 host tests and 10 protocol
tests pass. The build is byte-identical to the image already flashed for the
steering task; physical sensor calibration and wiring verification were not
performed. See
[Part 3.5 evidence and logs](CURRENT_SENSOR_HANDOFF.md#build-tests-and-persistent-evidence).
The figures, hash and QEMU results below describe the earlier preparation image.

Prepared on `lab2-integration`, following integration merge `3b04a43`.
Tianyi reports Parts 3.3/3.4 tested individually and confirms 3.5 unfinished.
No board was flashed, serial port opened, Pi contacted or actuator commanded
during this Part 4 preparation. This record does not certify hardware deadlines.

## Implemented

- One priority-1 actuator owner; status 2, dedicated current workqueue 3,
  console 4. Runtime error/boot diagnostics run outside the urgent owner.
  Build assertion prevents synchronized whole-line printk interrupt masking.
- 60 ms UART timeout implements three missed 20 ms commands. Pi UDP freshness
  remains 80 ms. The distinct upstream hazard behavior is documented in the task table.
- CMD_RX/PC2 and PWM_SET/PC3 trace outputs. Marker GPIO set/clear uses atomic
  bit writes instead of an ODR read/modify/write that could race motor pins.
- Opt-in Pi BCM17/27 markers, including fresh, refresh, invalid-input stop and
  stale-input stop UART writes. Pi imports libgpiod only when markers are enabled.
- Current sampling/cache/status interface with channel validity and expiry.
  Backend explicitly returns ENOSYS/unavailable; ADC remains disabled. No new
  current-based motor limit or fabricated reading.
- USB console logging and `diag`; saved calibration records the actually
  selected board's USB serial identity, not the old bench board's hardcoded ID.
- Offline CSV summary, reproducible build/configuration checker, bounded QEMU
  test runner, complete meeting guide, scope guide and blank measurement sheet.
- Part 4 questions answered against actual code. Future CAN-zone design is a
  separate draft for review, not implemented functionality or an agreed catalog.

## Verification

| Check | Result |
| --- | --- |
| NUCLEO-F401RE build via `windows/build_part4.ps1` | PASS; Zephyr v4.4.0-16655-g7a7003dec4b9, SDK 1.0.1 |
| Image size | 61,452 bytes flash, 15,872 bytes RAM |
| Generated pin/peripheral/configuration check | PASS: both motor timers enabled, servo independent, lamps and PC2/PC3 correct; ADC off; printk synchronization off |
| ARM/QEMU integration suite | **42 passed**: actuator/watchdog 7, blinkers 12, currents 4, existing motor contracts 4, self-test 8, servo 7 |
| Python discovery | **40 passed, 2 skipped** (native host GCC missing; C contracts run in QEMU) |
| Separate wire-protocol suite | **9 passed** |
| Python syntax checks | PASS for pi, windows and tools |
| Hardware/physical timing | Not performed |

The tests at that time covered validity, genuine numeric zero vs unavailable,
the unavailable backend, expiry, wraparound and recovery. That image's backend
was a stub; the current image acquires real ADC samples, and the native boundary
tests above cover its conversion instead. Electrical conditioning and workqueue
acquisition execution time remain untested.
The new timeout tests cover the three-missed-update boundary, refresh and clock
wrap; a logical timer test is not a physical latency measurement.

Firmware path: `build/part4/zephyr/zephyr.bin`.
SHA-256 of the verified binary:

```text
d7c5cef04be62b7682f4581ef489efa3e481627a2fc970372c4d0efc3f33f0a7
```

Logs (Git-ignored): `logs/integration/part4-final-build.log`,
`part4-python.log`, `part4-protocol.log`, `part4-qemu-final.log`.
The earlier `part4-qemu.log` predates the two watchdog tests. An initial protocol
test import failure was corrected by exposing the Pi helper module path in
the test harness; the final protocol run passes. No hardware was used to fix it.

## Reproduce software checks

Build commands are in the repository README. The production app is
`stm32_zephyr/`; the ARM/QEMU suite is `tests/integration/`. The bounded
runner is `tools/run_qemu_tests.py`. Use the installed Zephyr environment
and SDK; no machine-specific paths are required by the test source.

## Required next evidence

Use the [integration design](INTEGRATION.md) and [timing specification](PART4_TIMING.md): identify the
final motor board, deploy matching firmware/Pi modules, test all outputs and
fault/recovery behavior together, complete 3.5 and measure deadlines while
all normal tasks are active. Record the actual timing in the task table and
worksheet. The new steering policy needs a healthy link and centered wheel after
faults, not USB arm/live or keepalives. See [steering software results](STEERING_AUTONOMOUS.md)
for what has and has not been verified.
