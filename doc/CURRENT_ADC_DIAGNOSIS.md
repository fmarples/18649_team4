# ADC completion hang diagnosis, 2026-09-28

## Scope and result

The user authorized briefly stopping the running managed session and flashing
current-diagnostic firmware, without commanding motor or servo movement.
`stop.py` stopped the recorded GUI tree and Pi service before any flash.
No wheel restart, B1 action, serial command or actuator test occurred.

The production change is confined to `stm32_zephyr/src/current_backend.c`.
Instead of one eight-repeat, three-channel scan, it performs three eight-repeat,
single-channel reads. All reads must succeed before conversion/publication.
Pins, calibration, negative values, +4320 mA ceiling, period, priorities and
all actuator policies are unchanged.

## What the evidence establishes

The initial live Pi check failed with advancing status and current validity 0.
The previous passive capture placed the last successful sample near 1240 ms
of boot, while the rest of the MCU continued running. Ordinary returned read
errors would publish a new timestamp and errno, unlike this indefinitely aging
successful sample.

Temporary worker entry/return counters and non-printing ADC ISR counters were
added. The first diagnostic image ran for 33 seconds without an overrun after
the command stream was stopped. **The original live-session trigger was not
observed.** Stopping traffic changes interrupt load, and instrumentation changes
timing, so this run does not exonerate the driver or prove a spontaneous cause.

A second diagnostic image delayed one ADC ISR by 100 us after uptime 2000 ms.
This controlled hardware fault injection produced:

```text
ms=2149 enter=101 return=100 ovr=1 eoc=2401 done=800 missing_at_ovr=3
CURRENT ... valid=0 age_ms=145 error=0
```

The counters stayed fixed as uptime and sample age advanced. The old driver
consumed only one result from the affected three-channel scan. Its OVR branch
clears the flag but neither fails nor completes the transaction. The synchronous
completion semaphore waits forever for conversions already lost. This proves
that an actual overrun causes the observed permanent-staleness failure mode;
it does not retrospectively establish which interrupt caused the original one.

With the production fix and the identical 100 us delay still installed, the
ADC had no overrun and continued completing acquisitions beyond 12 seconds.
A single-channel conversion has no following channel to overwrite its data
register. The driver consumes it before starting its next repeat.

The external Zephyr driver and `current_sense.c` were then restored byte-for-byte
from pre-edit backups. No instrumentation or injected delay is in the final
image. This fix requires no external Zephyr patch or DMA configuration.

## Regression and final hardware verification

`tests/test_current_backend.c` exercises the real production backend and cache
with only the ADC boundary faked. The fake models delayed multi-channel service
as a bounded failure instead of hanging the test process. The new regression
failed against the old backend and passed after the fix. It also covers signed
currents, noise averaging, clip preservation, and all-or-nothing invalidation
when the second or third channel fails, followed by recovery. The fake is not
a simulation of the real ISR; the controlled hardware experiment supplies that
evidence.

The final uninstrumented image was flashed to ST-LINK
`066BFF505487525067171333`, rediscovered as COM4 and drive D: `NOD_F401RE`.
No `FAIL.TXT` appeared. The passive capture, with DTR/RTS false and no serial TX,
recorded:

- 243 CURRENT samples, all validity 7 and error 0.
- Age 2..15 ms, across DRIVE uptime 51..62847 ms.
- Target, reported drive duty and fault all zero; encoder counts stayed zero.
- WAITING for Pi commands throughout, with startup hazards as existing policy.
- No fatal report or diagnostic prefix.

This verifies non-driving software startup telemetry, not electrical boot/reset
pin levels. Mode 2 is the existing link-loss brake policy, not a claim that all
L298N enables are low. Servo startup announces waiting for healthy centered Pi
commands; no physical servo waveform or reset-transient measurement was made.

The numbers are not accepted current measurements: left and servo remained at
the +4320 mA ceiling, and right ranged -6131..-4908 mA. Negative values were
preserved. Actual sensor supply, output voltage, ground, connections, offsets
and reference need measurement. No calibration or wiring correction was made.

The final build and generated pin/configuration checks passed. Focused native
production-C current tests and the protocol tests passed. At this stage, the
managed command stream remained stopped and only idle operation had been
verified. The subsequent live-session recheck is recorded below.

## Images and persistent artifacts

All diagnostic artifacts below are under
`C:\Users\13982\18649_team4\logs\current-sense\`.
Matched `.bin` and `.elf` files are retained for each flashed image.

| Image | SHA-256 |
|---|---|
| diagnostic.bin, counters only | `202a3b5a09d32f5ee8a302956e64d6e2a3c86edc7ad45211ff4f5e63d7674bad` |
| injected.bin, old backend + one delay | `d79b6def4d9a45822756017c60c0b834233232435ba32db46507ae02f02d46b8` |
| fixed-injected.bin, fixed backend + same delay | `20c0c69d9054c37e5aae075f87554d082fd5aa1575e0b664ffd880c429a11dc4` |
| final.bin, no diagnostics | `eb46d9cf7c2ab5e5d3a50b768c70a7b0becd76180772ecc8887aeabcd8e3e924` |

- Full USB/fatal output: `diagnostic-console.log`, `injected-console.log`,
  `fixed-injected-console.log`, `final-console.log`.
- Flash identity/hash records: matching `*-flash.log` files.
- Build/generated checks: matching `*-build.log` files.
- RED/GREEN: `regression-red.log`, `regression-green.log`.
- Final host/protocol checks: `final-host-tests.log`, `final-protocol-tests.log`.
- Sustained passive assertions: `final-verification.log`, `verify_fix.py`.
- Driver/worker backups: `adc_stm32.c.original`, `current_sense.c.original`;
  restored hashes in `restore.log` match `instrument-backup.log`.
- Session stop: `session-stop.log`; launcher details also remain in
  `C:\Users\13982\18649_team4\logs\session\launcher.log`.
- Capture exceptions persist to `<label>.crash.txt`; verification exceptions
  to `verify-fix.crash.txt`. No such exception occurred in these runs. Native
  MCU dumps are unavailable; complete serial fatal output and matched ELF are
  the crash evidence path.

At completion of the flash/capture phase, the managed session was stopped: its
state file was removed by `stop.py`, recorded PID 30392 exited, its Pi unit was
inactive, and Pi UDP 8000 was unbound. No temporary server or serial handle
remained. No commit or global Git operation was performed.

## Ground correction and live-path recheck

The user then confirmed only A0 and A3 are connected and discovered both sensor
grounds were missing. They reported grounding the sensors and requested another
check. Their earlier OUT measurements, 3.824 V and 3.695 V, used Nucleo GND,
not the sensor module GND. Supplies were reported as approximately 5.22 V.
These pre-correction readings do not establish valid offsets or calibration.

By the recheck a new managed session was already running,
`lab2-wheel-20260927-162014-562e6d24.service`; the agent did not start or interrupt
it. The MCU had also restarted. Passive USB capture
`console-20260928-002435.log` recorded 31 CURRENT samples under LINK_OK, all
validity 7/error 0, age 2..20 ms. Propulsive duty and encoder counts remained
zero. A0 averaged 680.1 mA, range 577..782; A3 averaged 899.1 mA, range
814..1047, using the unchanged nominal conversion. Ceiling readings disappeared.
The unconnected A1 ranged -7132..-6378 mA and is not usable current data.

`python logs/current-sense/check_live_status.py` now passes against the live Pi
CSV. `python logs/wheel-gui/event-validation/check_live_gui.py` also passes:
20 fresh advancing CRC-valid status frames reached the actual GUI, A0/A3 were
not clipped, and categorized sensor events were saved without `No data` spam.
Evidence is `live-status-probe.log` here and `live-gui-check.log`,
`live-gui-frames.jsonl`, `live-gui-events.log` under
`logs/wheel-gui/event-validation/`. This verifies the MCU -> Pi -> GUI path
with a live wheel stream after the fix, beyond the earlier idle-only check.

The connected channels still need measured zero offsets, reference voltage
and sensitivity calibration. Nonzero nominal values at zero propulsive duty
are not proof of actual load current or of a known zero-current condition.
No calibration was guessed or automatically zeroed. The running user session
was preserved, and passive serial handles were closed.

Final combined verification: 63 host tests and 10 protocol tests passed;
Python syntax and Git whitespace checks passed. Test logs are under
`logs/wheel-gui/event-validation/`.
