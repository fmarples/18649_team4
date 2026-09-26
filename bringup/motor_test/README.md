# L298N motor bench test — NUCLEO-F401RE

> **CURRENT FLASHED PROFILE: startup 60% / 200 ms; kick/hold 60% / 200 ms then
> 55% / maximum 4000 ms.** Forward only, fixed per build, no boot actuation.
> ARM then BOTH for startup, or HOLDBOTH for the two-stage trial. Either wheel's
> 150 ms no-progress/reversal guard stops both and latches a fault.
> The user now requires both motors together. Simultaneous startup passed 3/3 at
> 55% and failed at 50%; simultaneous 4-second holding passed 3/3 at 40% and failed
> at 35%. Final reflash was idle-checked only; both outputs disabled and stationary.
> See [measurements and limits](../../doc/MOTOR_CHARACTERIZATION.md). No velocity controller.

Standalone Zephyr bring-up firmware. **No automatic drive command on boot.** It is separate
from the Part 2 link app and replaces the encoder diagnostic when flashed.
It now reports raw x4 encoder counts alongside motor status. It does not run PID,
steering, current sensors, blinkers, or the Pi protocol. Encoder counts now drive
a motion cutoff, but not closed-loop speed regulation or current limiting.

## Hardware and startup

Use the [confirmed motor-control pin assignments](../../doc/STM32_PINOUT.md)
and [external E5V power configuration](../../doc/HARDWARE.md#current-power-setup).
The user reported the six motor-control wires connected, confirmed the ENA/ENB
jumper caps removed, and reported the chassis supported with wheels clear.
The user confirmed the separate 5V-EN regulator jumper is installed and measured
the driver's +5V terminal to GND at 5 V. Physical wiring, motor rail/output voltage
under load, and current limits have not been independently verified.

Firmware initializes IN1–IN4 low and sets ENA/ENB PWM to zero. PWM uses
PB4/TIM3_CH1 and PB10/TIM2_CH3, each at **10 kHz**. GPIO pin readbacks are reported
at 20 Hz over the ST-LINK serial console (115200 baud, 8-N-1), increased from
4 Hz to observe the short 200 ms kick.

**Startup limitation:** software cannot guarantee inactive pins during reset or
before pinctrl initialization. Internal PWM-pin pulldowns apply only after
initialization; hardware enable pulldowns would be needed for a defined reset
state. The user explicitly accepted the possibility of startup motion on the
raised chassis and requested flashing without another motor-power isolation
step. Do not mistake that acceptance for verified reset safety or a final design.

## Explicit, bounded bench commands

ASCII, uppercase, newline-terminated, through **ST-LINK console**, not Pi UART:

| Command | Action |
|---|---|
| `STATUS` | Report both compiled profiles, stage durations and 10 kHz PWM; no actuation. |
| `STOP` | Disarm, purge pending commands, disable both PWM outputs. |
| `ARM` | Arm one test for 5 seconds; outputs remain disabled. |
| `LEFT` | Only after ARM: left forward at compiled duty, maximum 200 ms. |
| `RIGHT` | Only after ARM: right forward at compiled duty, maximum 200 ms. |
| `BOTH` | Only after ARM: both forward at compiled startup duty, maximum 200 ms. |
| `HOLDBOTH` | Only after ARM: both forward at 60% for 200 ms, then compiled holding duty for its bounded duration. |
| `HOLDLEFT` / `HOLDRIGHT` | Same two-stage profile on one wheel; retained for diagnostics, not the agreed measurement case. |

A start consumes the arm. Duplicate/retrigger/invalid commands stop and disarm;
there is no arbitrary-duty or continuous-run command. Each pulse must be armed
again. LEFT now selects IN1=0/IN2=1 (forward); RIGHT selects IN3=1/IN4=0
(forward). BOTH uses IN=0110. An unselected channel remains disabled. Stopping
sets enable PWM to zero and IN1–IN4 low: **coast**, not dynamic braking. Encoder
traces show substantial movement continuing after enable goes low.

Each enabled wheel must advance at least 4 raw counts in its calibrated forward
direction within 150 ms of starting and of each progress event. Left-forward is
negative raw counts; right-forward is positive. Four reverse counts also trip.
Motion faults latch: 1=left stalled, 2=right stalled, 3=left reversed, 4=right
reversed. Any invalid quadrature transition or GPIO error also stops both outputs
(negative HAL/error code). STOP does not clear a fault; reboot is required.
These are software checks, **not overcurrent protection** or a hardware watchdog.

A priority-2 thread owns motor outputs and checks expiry every approximately
1 ms. It starts only after hardware initialization. Console printing happens
in the priority-5 main thread and cannot hold a lock around motor I/O. A build
assertion enforces that the control thread outranks the console thread. The
earlier images incorrectly retained main priority 0; this was corrected after
the single 5-second trial. Deadlines still have scheduling/driver latency.
UART RX interrupts capture bytes into a 128-byte queue; the main thread parses
complete lines. Malformed/overlong serial input, RX/command queue overflow,
UART receive errors, stale queued commands, and partial-line timeout request a stop. HAL errors latch a fault and attempt to
reclaim the enable pins as GPIO-low; operation does not resume until reboot.

The startup 200 ms cap and holding-stage cap are software deadlines plus
scheduling/driver latency, **not scope-measured guarantees**. It is not protection against a
CPU/kernel hang, shorted driver, or overcurrent. No independent hardware cutoff/
current limit is implemented. Neither 20% nor 35% moved either wheel; a
50% / 500 ms left trial also failed. The subsequent unloaded 100% / 3000 ms
measurement produced 12 V. That unloaded image was replaced before resuming
connected-motor testing: first 50% / 1000 ms, then separate 100% / 200 ms kicks,
then the user-requested guarded simultaneous forward trial at 100% / 5000 ms.
The subsequent startup sweep replaced that profile with a 200 ms cap, retaining
the motion guard and changing only the compiled duty between trials.

## Build and flash

Use the environment in [encoder bring-up](../encoder_test/README.md). From the
Zephyr workspace with its virtualenv on PATH:

```powershell
west build -b nucleo_f401re -d C:\Users\13982\18649_team4\build\motor-test C:\Users\13982\18649_team4\bringup\motor_test -o=-j4 -- -DMOTOR_TEST_DUTY=60 -DMOTOR_HOLD_DUTY=55 -DMOTOR_HOLD_MS=4000
```

`MOTOR_TEST_DUTY` accepts integers 1 through 100 and defaults to 60. Pass it
explicitly: CMake retains the previous value in an existing build directory.
The startup pulse limit stays 200 ms for every duty. `MOTOR_HOLD_DUTY` accepts
1–60 and defaults to 55; `MOTOR_HOLD_MS` accepts only 2000 or 4000 and defaults
to 2000 in a fresh build. The current flashed image and batch runner explicitly
select 4000. HOLD commands always kick at 60%, independently of the startup-test
duty. Each profile change requires rebuild/reflash. No serial command changes duty.
`build/` is gitignored. Rediscover the board drive and COM port before use. On
this host they were `D:` (`NOD_F401RE`) and `COM4` for the recorded flash. Copy
`build/motor-test/zephyr/zephyr.bin` to the board drive as `motor.bin`, check for
`FAIL.TXT`, then verify runtime over serial. Copy success alone is insufficient.

## One-command simultaneous sweep

**This physically drives both motors.** Rediscover COM port and board drive,
confirm raised wheels/common ground/power, and retain access to the motor-power
cutoff. The shared 12 V / 2 A adapter has not been qualified for motor current.
Never run a powered sweep as part of a general test or commit workflow.

On this Windows host, from the repo root, with an external 900-second timeout:

```text
C:\Users\13982\zephyrproject\.venv\Scripts\python.exe tests/run_motor_sweep.py --port COM4 --drive D --run --allow-stall-reset
```

Omit `--run` to print the plan without touching hardware. The script uses the
installed Zephyr workspace and GCC paths documented in the bring-up instructions.
It verifies the NOD_F401RE volume label before each flash and verifies the runtime
profile after flashing. It does not install drivers or repair the power setup.

- Startup duties: 60%, 55%, 50%, each from stationary encoders, capped at 200 ms.
- Holding duties: 55%, 50%, 45%, 40%, 35%, each after the 60% / 200 ms kick, capped
  at 4 seconds. Both wheels get the same duty; either wheel's guard stops both.
- Each descent stops at its first failure. Two further trials confirm the lowest
  passing setting. An inconsistent confirmation aborts rather than silently raising
  duty or retrying the failure. Untested values between steps remain unknown.
- A three-second warning and verified rest precede each trial. The runner records
  failed starts as failures even when the measurement process exits normally.
- `--allow-stall-reset` is explicit permission to proceed after expected latched
  stall faults 1/2, after verifying disabled outputs and stationary encoders and
  reflashing. Without it, the first motion fault aborts the batch. Failed duties
  are never retried automatically. Reverse/HAL/encoder/reset errors always abort.
- Success restores startup 60% / 200 ms and hold 55% / 4000 ms, then checks idle.
  Error exit requests STOP and attempts to verify rest without clearing the fault.

The batch writes `logs/motor-bench/sweep-<timestamp>/summary.json`, per-step build,
flash and trial logs, and `crash.txt` / `cleanup-crash.txt` on errors. Individual
raw traces remain in `logs/motor-bench/startup-both-*.json` and `hold-both-*.json`;
exceptions also write matching `.crash.txt` stack traces. Native MCU crash dumps
are unavailable over the configured serial/mass-storage interface.

For a single authorized holding trial, external timeout 25 seconds:

```text
C:\Users\13982\zephyrproject\.venv\Scripts\python.exe tests/check_motor_hold.py --port COM4 --side BOTH --hold-duty 55 --hold-ms 4000 --run
```

Those arguments verify the flashed profile; they do not change it. `SAMPLE` frames
pair MCU-timestamped encoder counts with stage/applied duty/fault. Speeds use the
last approximately one second of HOLD, calibrated at 1320 counts/rev, with LEFT
negated before averaging. `ENC` and `MOTOR` frames remain available. The transition
briefly disables PWM while updating outputs, about one configured PWM period;
late speed windows exclude the transition and subsequent coast-down.

The complete batch and preliminary separate-wheel results are documented in
[Motor characterization](../../doc/MOTOR_CHARACTERIZATION.md). The final batch
completed 12 powered trials: ten passes and two expected cutoff failures, then
verified idle after the final reflash. This is not current-limit or loaded testing.

## Startup sweep, 2026-09-27

This earlier section records **separate-wheel tests**, superseded as the operating
case by the simultaneous measurements above. The user later selected automated
sequencing with checked resets after expected stall faults.

The user reconfirmed raised wheels, unchanged wiring and power ready, and selected
both motors tested separately. Every pulse began after at least one second of
stationary encoder telemetry and a three-second warning. PWM stayed at 10 kHz;
forward polarity and the shared 12 V / 2 A supply were unchanged. Each image had
a 200 ms cap and the same 150 ms no-progress guard. No ramp, running-duty test,
frequency change or simultaneous start was performed.

| Duty | Left starts | Right starts | Result |
|---|---|---|---|
| 50% | 0/1 | 0/1 | Only 1–2 forward counts; guard latched fault 1/2 and disabled outputs. |
| 55% | 3/3 | 3/3 | Forward motion during powered telemetry, no faults. |
| 60% | 1/1 | 1/1 | Forward motion during powered telemetry, no faults; user also confirmed movement. |

Execution order was 60% left/right, 55% left/right, 50% left/right with a deliberate
same-duty reflash between faulted trials, then two more 55% starts per side.
Reflashes never armed a motor. Ten powered trials total. Every trial ended with
disabled outputs and stationary encoder counts; no invalid transitions or GPIO
errors were reported. The unselected encoder stayed unchanged during each pulse.
The initial 50% tests in earlier sessions drove LEFT backward; today's 50%
forward recheck independently established the lower failed setting.

**Lowest tested passing duty: 55% on both motors.** The observed transition lies
above 50% and at or below 55% for these short, unloaded starts. 51–54% are untested,
and three passes are not a reliability qualification. Use 60% as a provisional
startup-kick candidate with margin, not a validated ground-loaded or simultaneous
startup guarantee. Holding duty, target speed, startup current and temperature
remain unmeasured. The sweep does not identify the electrical cause of the threshold.

The last encoder samples paired with active status showed absolute forward deltas
of 70/73/76 counts for LEFT at 55%, 79/75/79 for RIGHT at 55%, and 111/141 at 60%.
These are discrete telemetry observations, not exact powered-interval totals.
Coast-down counts are excluded from the startup verdict and are not divided by
200 ms to infer speed. Host command-to-IDLE observations were about 0.20 seconds
for guard-aborted starts and 0.25–0.27 seconds for completed pulses. USB/console
latency means those are not physical PWM timing measurements.

Local evidence, under `logs/motor-bench/`:

- `startup-left-60-20260927-035157.json`, `startup-right-60-20260927-035229.json`
- `startup-left-55-20260927-035314.json`, `startup-right-55-20260927-035323.json`
- `startup-left-50-20260927-035414.json`, `startup-right-50-20260927-035505.json`
- `startup-left-55-20260927-035554.json`, `startup-right-55-20260927-035606.json`
- `startup-left-55-20260927-035616.json`, `startup-right-55-20260927-035625.json`
- Build/flash captures: `startup-prepare-*.log` and `startup-prepare-*.json`.
  Final image/idle capture: `startup-prepare-60-20260927-035649.json`.

The initial old-image idle check lost telemetry without any actuation; its cause
was not diagnosed. Reflash restored streaming. One right-60 invocation stopped
before ARM because the opening serial fragment joined the profile response.
`startup-right-60-20260927-035209.json` and `.crash.txt` preserve that failure.
The script now drains opening fragments before requesting STATUS; the subsequent
real-board run passed. No powered pulse was retried automatically.

Run exactly one authorized startup trial, with an external 20-second timeout:

```text
C:\Users\13982\zephyrproject\.venv\Scripts\python.exe tests/check_motor_startup.py --port COM4 --side LEFT --duty 60 --pulse
```

`--duty` is an expected-profile interlock, not a command to change firmware duty.
The script requires matching STATUS, disabled outputs and rest before ARM, checks
forward encoder motion and the other channel, waits for coast-down, and sends STOP
on exit. A selected-wheel no-progress fault is recorded as `NO_START`, not a
successful start. Partial starts and insufficient movement are explicit failed
verdicts, not successful tests. Reverse/encoder/HAL faults abort. Faults stay latched
until reboot. The individual checker never clears or retries a fault; only the
explicitly authorized batch workflow above may reflash after an expected stall.
The old `check_motor_direction.py` entry point calls this bounded check and also
requires `--duty`; its former five-second behavior is retired. BOTH now uses 200 ms.

Captures persist as `logs/motor-bench/startup-<side>-<duty>-<timestamp>.json`.
Failures also persist stack traces as matching `.crash.txt` files. This host cannot
produce native MCU crash dumps over mass-storage/serial; serial errors and reset
banners are captured instead. Local `build/` and `logs/` remain ignored.

## Tests and verification status

Host command/output tests (run with an external 20-second timeout):

```text
gcc -std=c11 -Wall -Wextra -Werror -Ibringup/motor_test/src tests/test_motor_bench.c bringup/motor_test/src/bench_control.c -o build/motor-host-test/test.exe
build/motor-host-test/test.exe
```

Create `build/motor-host-test/` first. On this machine the compiler is
`C:\msys64\mingw64\bin\gcc.exe`.

Board idle check (external timeout 15 seconds; sends only STOP/STATUS):

```text
C:\Users\13982\zephyrproject\.venv\Scripts\python.exe tests/check_motor_idle.py --port COM4 --seconds 4
```

Current-profile verification: host output/deadline/guard tests passed for 50%,
55% and 60% builds; holding tests also cover single/BOTH stage transitions,
2000/4000 ms caps and either-wheel cutoff. Startup, MCU-speed and automated
sequence regression tests passed; built PWM configuration
remained 100000 ns for both channels. Hardware results are in the sweep above.
For a nondefault host profile, pass both `-DBENCH_DUTY_PERCENT=55` and
`-DEXPECTED_DUTY=55` to GCC. Run verdict tests with an external timeout:

```text
python -m unittest discover -s tests -p "test_motor_*.py"
```

Historical verification follows; profile values below describe those earlier images.

Completed:

- Host tests passed: boot/unarmed inputs disabled; ARM alone disabled; left or
  right only at fixed duty (20%, then 35%, then 50%); expiry at 500 ms; STOP;
  5-second arm timeout; retrigger/switch rejection and invalid-command disarm.
  The 35% expectations failed against the old 20% implementation, then passed
  after updating the fixed duty. The same RED/GREEN check passed for the 50%
  update; normal-speed ARM/STOP reception was reverified after flashing.
- Board idle test first failed against encoder-only firmware (no MOTOR frames).
- Zephyr v4.3.0 / SDK 0.17.4 build succeeded and was flashed via USB mass storage.
- Real-board idle test passed with 17 frames, each reporting:

  `MOTOR phase=IDLE left=0 right=0 in=0000 en=00 fault=0 accepted=0 rejected=0`

- Initial movement attempt stopped before sending a pulse: ordinary-speed ARM
  was not acknowledged. `tests/check_motor_commands.py --port COM4` reproduced
  this; its `--paced` diagnostic (30 ms/byte) passed. The original 1 ms RX polling
  could not reliably receive 115200-baud bursts on the F401 USART. Replacing
  polling with interrupt-driven RX plus a byte queue made the normal-speed
  command-only regression pass (ARM, then STOP; no motor output).
- After reflashing the RX fix, left and right were each commanded separately
  at 20% for nominal 500 ms. Telemetry reported LEFT/20/0 with IN=1000, then
  IDLE/0/0/IN=0000/EN=00; similarly RIGHT/0/20 with IN=0010, then idle. No
  faults were reported. Raw local captures are in ignored
  `logs/motor-bench/first-pulses.json` (initial failure) and
  `logs/motor-bench/pulse-verification.json` (post-fix command/output pass).
- **Physical result: the user reports neither wheel moved and a beep was heard.**
  Successful command/output telemetry is not a successful motor-motion test.
  Source of the sound, driver power/logic rails, connections, startup duty,
  and current limits still need checking. A repeated 20% test did not let the user
  localize the sound. The user subsequently explicitly requested higher duty.
- The 35% firmware was built/flashed; command-only ARM/STOP regression passed.
  Each channel then received one nominal 500 ms pulse at 35%, separately, and
  returned to idle with IN=0000/EN=00 and no firmware faults. The user reports
  **still only the beep, with no wheel movement** at 35%. This is not a successful
  motor bring-up. Local captures are in ignored `logs/motor-bench/duty35-*.json`.
  Check the shared driver power/logic supply, jumper configuration, and actual
  output voltage before escalating duty further.
- After the measured 5 V logic-rail confirmation, only the left channel received
  one 50% / nominal 500 ms pulse. LEFT/50/0/IN=1000 was followed by
  IDLE/0/0/IN=0000/EN=00 with no faults; the right channel remained disabled.
  The user reports **no wheel movement at 50%** and now believes the beep comes
  from the H-bridge. Capture: `logs/motor-bench/left-duty50-*.json`. Do not keep
  escalating duty without checking the driver output/power path and connections.
- The earlier wiring photo embedded in the shared conversation shows black
  Dupont connector housings at both motor output screw-terminal pairs. Whether
  exposed metal is properly clamped cannot be established from the photo; the
  user subsequently confirmed the screw terminals clamp **exposed male Dupont
  pins**, not plastic female housings. Electrical continuity has not been measured;
  the photo alone does not establish a bad connection.
- A further left 50% / nominal 500 ms pulse was used with a DC multimeter
  across OUT1–OUT2. The user saw approximately **0.3 V momentarily**, but the
  meter has no MAX capture and may have missed/averaged the short pulse.
  This is **inconclusive**, not evidence of a measured 0.3 V steady output.
  Capture: `logs/motor-bench/left-output-voltage-*.json`.
- The user confirmed disconnecting the motor from OUT1–OUT2 and positioning
  the meter across the unloaded output. A left-only 100% / 3000 ms firmware
  was built and flashed. Host RED/GREEN checks covered duration/duty and RIGHT
  rejection; STOP, arm expiry, retrigger and invalid-command disarm also passed.
  The board acknowledged ARM/STOP; ARM/RIGHT was explicitly rejected with both
  outputs disabled. Then one ARM/LEFT produced repeated LEFT/100/0/IN=1000/EN=10
  frames for roughly 3 seconds, followed by IDLE/0/0/IN=0000/EN=00. No faults.
  Capture: `logs/motor-bench/left-unloaded-dc-*.json`. The user measured **12 V
  across unloaded OUT1–OUT2** during this test. This establishes a functioning
  unloaded DC output path, not loaded current capability or correct partial-duty
  behavior. At that stage the motor remained disconnected and the unloaded
  diagnostic was flashed; subsequent profiles and reconnection are recorded below.
- With power off and the left motor disconnected, the user measured **3.2 ohms**
  across its two power leads. This indicates continuity, not proof of motor health.
  The simple 12 V / 3.2 ohm estimate is about 3.75 A at standstill before bridge
  and wiring losses; this is not a measured stall current or validated rating.
  Supply sag, driver/power-path losses, and insufficient PWM starting torque
  remain possible. The user reports the shared adapter is rated **12 V, 2 A**.
  Startup overload/supply sag is plausible, but has not been measured and is not
  established as the cause. Do not use the 3-second full-duty diagnostic with a motor.
- Only the 12 V / 2 A adapter and multimeter are available; no current-limited
  bench supply. A LEFT-only 50% / 1000 ms profile was prepared for measuring the
  L298N input rail under load. Host RED/GREEN checks and the Zephyr build passed.
  The user reconnected the left motor, restored power, and measured **12 V idle**
  directly at the L298N input. New firmware was flashed, with its 50% / 1000 ms
  banner confirmed before actuation. A transient board-drive access error just
  after flashing cleared on recheck; no FAIL.TXT. ARM/STOP reception passed.
  One LEFT/50/0/IN=1000 pulse then returned to IDLE/0/0/IN=0000/EN=00 with no
  observed firmware fault/reset. Capture: `logs/motor-bench/left-supply-sag-*.json`.
  At the user's request the same pulse was repeated once; it again returned to
  idle without observed faults/reset. Capture: `logs/motor-bench/left-supply-sag-repeat-*.json`.
  The user reports **no apparent input-voltage drop and no wheel movement**.
  This weakens sustained supply sag as the explanation; a slow meter may miss
  brief transients, so it does not exclude all supply sag. The next measurement
  was loaded OUT1–OUT2 voltage during the same bounded pulse.
- The loaded OUT1–OUT2 measurement at 50% / 1000 ms again displayed approximately
  **0.3 V**, per the user (`logs/motor-bench/left-loaded-output-*.json`). The prior
  12 V unloaded measurement used 100% duty, so load and duty both differ; these
  results alone do not establish a faulty driver. A proposed 1 kHz frequency
  comparison was interrupted before implementation; timers remain configured at
  10 kHz. `tests/check_motor_pwm_config.py --period-ns 100000` verifies the built
  timer configuration, not a physical waveform.
- The user requested 100% / 3 seconds, then accepted the recommended **single
  100% / 200 ms** connected-motor kick instead. Host duty/duration tests failed
  against the previous profile, then passed with the new profile; RIGHT rejection,
  STOP, expiry and invalid/retrigger disarm checks passed. The build was flashed,
  its 100% / 200 ms startup banner verified, and ARM/STOP reception passed.
  One LEFT/100/0/IN=1000/EN=10 kick returned to IDLE/0/0/IN=0000/EN=00 with no
  observed fault/reset. Capture: `logs/motor-bench/left-startup-100pct-200ms-*.json`.
  **The user confirmed: "that turned it."** This is the first reported powered
  wheel movement. At that stage wheel identity and vehicle-forward polarity
  still needed confirmation; both were subsequently verified below. The result
  supports investigating startup/PWM behavior rather
  than assuming a dead motor/driver; it does not identify the exact cause or
  validate current capability. No automatic repetition was used.
- Encoder observation was added using the hand-turn-verified quadrature decoder
  and pin assignments. The existing encoder-streaming check failed before this
  change (no ENC frames), then passed after build/flash. Motor idle checks passed.
  GPIO read errors request a stop and latch a fault; invalid-transition counts
  are reported and rejected by the direction-test script.
- `tests/check_motor_direction.py --port COM4 --pulse` observed LEFT moving
  **backward**: raw left delta +4987 over the pulse plus initial coast window,
  right unchanged, no invalid transitions/errors. A later passive capture was
  stationary at left=6028/right=0. The user confirmed backward direction.
- RIGHT was re-enabled for separate, bounded kicks (host RED/GREEN for its
  200 ms expiry, no simultaneous drive, and STOP/invalid/retrigger checks).
  After reflash and ARM/STOP verification, `tests/check_motor_direction.py
  --port COM4 --side RIGHT --pulse` observed RIGHT moving **forward**: raw
  right delta +5041 over the pulse plus initial coast window, left unchanged,
  no invalid transitions/errors. Both output channels returned to disabled.
  Captures: `logs/motor-bench/encoder-direction-*.json`. Coast-window count totals
  are not counts during just the 200 ms powered interval or speed measurements.
- The user explicitly chose **both together for 5 seconds** after the shared
  12 V / 2 A supply limitation was explained. Left direction was inverted to
  forward; BOTH and a latched per-wheel motion guard were implemented. Host tests
  cover the 5000 ms limit, 150 ms no-progress stop, either wheel stopping or
  reversing, nonzero baselines, insufficient progress, STOP, rearm blocking after
  faults, arm expiry and invalid/retrigger commands. Deliberate physical stalls
  were not tested; these checks do not measure current or guarantee reset safety.
- After build/flash, the 100% / 5000 ms profile, forward IN=01/10 and motion-guard
  banner were verified; ARM/STOP passed. **Exactly one** `--side BOTH --pulse`
  trial then completed. BOTH/100/100/IN=0110/EN=11 lasted nominally 5 seconds;
  host command-to-idle acknowledgment was **5.016 s**. Calibrated encoders confirmed
  both forward: left **-37257**, right **+38590** counts over the run plus initial
  coast capture, with zero invalid transitions/GPIO errors and no firmware faults.
  Final outputs were IDLE/0/0/IN=0000/EN=00. Capture:
  `logs/motor-bench/encoder-direction-both-20260927-033301.json`.
- Post-trial inspection found main priority 0 outranked control priority 2.
  A compile-time priority assertion first failed; setting main priority 5 made
  the build pass. The priority-corrected image was flashed, its runtime
  `SCHED control=2 console=5` banner confirmed, and 20 idle frames passed. Encoder
  counts remained stationary. **No further motor command or repeat trial** was
  sent after this correction. The timing guards have host tests, not a physical
  induced-stall latency measurement on the final image.
- PWM waveform quality, precise physical pulse duration, braking, long-term or
  ground-loaded operation, speed accuracy and electrical/current limits remain
  unverified. Neither the earlier 250 ms nor current 50 ms status interval
  establishes exact pulse timing. Low-duty starting behavior remains unresolved.
