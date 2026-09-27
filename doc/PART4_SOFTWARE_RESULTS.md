# Part 4 preparation: software evidence and remaining hardware work

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

The current tests cover validity, genuine numeric zero vs unavailable, missing
backend, expiry, wraparound and recovery. The actual ADC backend, electrical
conditioning and workqueue acquisition execution time remain untested.
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

From this checkout in PowerShell on Tianyi's laptop:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\build_part4.ps1
$labPython = 'C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts\python.exe'
& $labPython -m unittest discover -s tests -p 'test_*.py' -v
& $labPython test_protocol.py -v
$integrationRepo = (Get-Location).Path
$env:Path = 'C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts;' + $env:Path
$env:ZEPHYR_SDK_INSTALL_DIR = 'C:\Users\hetia\zephyr-sdk-1.0.1'
Push-Location 'C:\Users\hetia\CMU\18649\zephyrproject'
west build -b qemu_cortex_m3 "$integrationRepo\tests\integration" -d "$integrationRepo\build\integration-tests" -o=-j4
Pop-Location
& $labPython tools/run_qemu_tests.py --qemu C:\Users\hetia\zephyr-sdk-1.0.1\hosttools\qemu\qemu-system-arm.exe --log ('logs/integration/qemu-' + (Get-Date -Format yyyyMMdd-HHmmss) + '.log')
```

These commands do not flash or use COM ports. The QEMU runner stops only the
emulator it launched, after a success/failure result or a bounded timeout.

## Required next evidence

Follow [PART4_START_HERE](../PART4_START_HERE.md) with the team: identify the
final motor board, deploy matching firmware/Pi modules, test all outputs and
fault/recovery behavior together, complete 3.5 and measure deadlines while
all normal tasks are active. Record the actual timing in the task table and
worksheet. Servo still needs explicit arm/live and a USB heartbeat after faults.
