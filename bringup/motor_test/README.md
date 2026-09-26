# L298N motor bench test — NUCLEO-F401RE

> **CURRENT SOURCE AND FLASHED FIRMWARE: forward-only, 100%, maximum 5 seconds.**
> ARM then LEFT, RIGHT or BOTH. A per-wheel 150 ms no-progress cutoff, reverse
> motion check, and encoder-error checks stop BOTH outputs and latch a fault.
> ONE simultaneous 5-second forward trial passed; both outputs returned to idle.
> A subsequent scheduling-priority correction was flashed and idle-checked only;
> the motor trial was not repeated. Bench firmware, not a closed-loop controller.

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
| `STATUS` | No actuation; status is already reported periodically. |
| `STOP` | Disarm, purge pending commands, disable both PWM outputs. |
| `ARM` | Arm one test for 5 seconds; outputs remain disabled. |
| `LEFT` | Only after ARM: left forward at 100%, maximum 5000 ms. |
| `RIGHT` | Only after ARM: right forward at 100%, maximum 5000 ms. |
| `BOTH` | Only after ARM: both forward at 100%, maximum 5000 ms. |

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

The current source's 5000 ms limit is a software deadline plus scheduling/driver
latency, **not a scope-measured guarantee**. It is not protection against a
CPU/kernel hang, shorted driver, or overcurrent. No independent hardware cutoff/
current limit is implemented. Neither 20% nor 35% moved either wheel; a
50% / 500 ms left trial also failed. The subsequent unloaded 100% / 3000 ms
measurement produced 12 V. That unloaded image was replaced before resuming
connected-motor testing: first 50% / 1000 ms, then separate 100% / 200 ms kicks,
then the user-requested guarded simultaneous forward trial at 100% / 5000 ms.

## Build and flash

Use the environment in [encoder bring-up](../encoder_test/README.md). From the
Zephyr workspace with its virtualenv on PATH:

```powershell
west build -b nucleo_f401re -d C:\Users\13982\18649_team4\build\motor-test C:\Users\13982\18649_team4\bringup\motor_test -o=-j4
```

`build/` is gitignored. Rediscover the board drive and COM port before use. On
this host they were `D:` (`NOD_F401RE`) and `COM4` for the recorded flash. Copy
`build/motor-test/zephyr/zephyr.bin` to the board drive as `motor.bin`, check for
`FAIL.TXT`, then verify runtime over serial. Copy success alone is insufficient.

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
