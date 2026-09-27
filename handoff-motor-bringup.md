# Handoff: continuous motor PID bench

> Historical handoff, superseded by the subsequent full-duty measurement and
> Pi-link motor integration. The board was last verified stopped after the
> 100%-duty trial and remains on that bench image. The integrated root image is
> built/host-tested but not flashed; the Pi end-to-end test was deferred.
> Use `AGENTS.md`, `PROTOCOL.md` and `doc/MOTOR_CHARACTERIZATION.md` for current
> decisions and state. References below to a running session or missing motor
> integration describe the earlier session, not the present checkout.

## Session endpoint

Startup/holding characterization and continuous encoder-based PID are implemented in the independent `bringup/motor_test/` application. Commit `f26e131eff31c9e411e16b7bed47f1f4cb5b6b94`, `feat: add continuous motor PID control with latched B1 stop`, is pushed to `origin/main`. The preceding characterization commit is `f707e59`.

The working tree was clean before this handoff update. This document update is not yet committed. Root `stm32_zephyr/` remains the team's link-only application. PID is not integrated with the Pi command path.

## Check hardware state before doing anything

**The user requested leaving both motors running continuously at 45 RPM until B1 or STOP.** No stop, reset, reflash, or restart was performed during commit or this handoff update. Do not interrupt that operation as incidental cleanup, and do not restart automatically if it has stopped.

The latest saved state inspected during this update says RUNNING, fault zero, at MCU time 70528 ms. The serial log ends at MCU time 70575 ms with filtered left/right RPM 42.136/48.057, average 45.096, and equal 45.171% duty. The last button record is released and unlatched. These are saved observations, not proof of current operation or logger health. No final stop verification or physical B1 press-to-stop result appears in the inspected tail.

Use these local artifacts before opening serial or taking hardware action:

- `logs/motor-bench/continuous-session.json`: background session ownership and stop route; recorded logger PID 3008. Verify ownership before relying on a PID that could be reused.
- `logs/motor-bench/continuous-20260927-055111/state.json`: last published status.
- `logs/motor-bench/continuous-20260927-055111/process.log`: logger output and exceptions.
- `logs/motor-bench/pid-45-20260927-055111.serial.log`: flushed telemetry.
- `logs/motor-bench/continuous-flash-20260927-055105/summary.json`: flash and idle/profile evidence.

Do not contend with an existing logger for the serial port. Last observed interfaces were COM4 and D: labeled `NOD_F401RE`; rediscover them before future hardware use. B1 is the independent local software stop. On a user-requested host stop, `python bringup/motor_test/stop.py` asks the existing logger to send STOP and verify outputs/rest. It does not kill the logger or reset the MCU.

## Decisions the next session must preserve

The user explicitly superseded the earlier four-second PID trial and agent-added operating limits:

- Continuous PID has no duration limit or heartbeat cutoff.
- Intentional manual holding/backdriving is allowed. PID has no stall/no-progress or reversal cutoff.
- Retain the measured startup/sustaining thresholds: 60% for a 200 ms startup kick, then a user-selected 40% running floor and full 100% PWM authority.
- B1, STOP, and PID 0 override the floor to zero and coast both motors. B1 latches off until reset; releasing it must not restart motors.
- Actual sensor/GPIO failures and invalid controller data still stop control.
- Do not add operating caps or restrictions without a lab requirement, confirmed component datasheet, or explicit user decision. See `AGENTS.md`.

The current controller is plain PID on average forward encoder RPM, with equal duty to both wheels. Feedforward, wheel balancing, and a separate integral clamp were removed. Average-speed regulation does not promise equal individual wheel speeds. Startup/HOLD diagnostics still have their own bounded profiles and motion guards; do not apply their restrictions to PID.

There is no implemented current limiting or thermal protection. The thresholds came from raised-wheel tests, not indefinite stall qualification. B1 is not a hardware emergency-stop circuit. Detailed controller constants, calibration, timing, and commands belong in the bench README, not a second specification here.

## Read these artifacts

- `AGENTS.md`: project scope, operating-limit decision, and hardware evidence rules.
- `bringup/motor_test/README.md`: current PID behavior, launch/stop commands, build/test commands, profiles, and persistent log/crash-report locations.
- `doc/MOTOR_CHARACTERIZATION.md`: simultaneous startup/holding measurements, first bounded PID result, subsequent continuous revisions, and evidence paths. Earlier feedforward/balancing results do not validate the current plain PID revision.
- `doc/HARDWARE.md`, `doc/STM32_PINOUT.md`, `doc/ENCODER_SPEC.md`: power, wiring, B1 mapping, calibration, and remaining electrical uncertainties.
- `bringup/encoder_test/README.md`: installed Windows/Zephyr tools and flashing workflow.
- `doc/18-449_649 Lab2 - Sensors and Actuators v1_0.pdf`: Lab 2 requirements, including average encoder velocity for control. `doc/18-449_649 Lab 1 - Requirements.pdf` is also tracked; do not import its later-system scope into this bench task.
- `doc/INTEGRATION.md`, `PART4_TASK_TABLE.md`, `PROTOCOL.md`: integration design and current CRC link protocol.

## Implementation and verification

Commit `f26e131` contains the implementation and regressions:

- `bringup/motor_test/src/velocity_control.c` and `.h`: actual-dt velocity estimation, filtered measurement, full PID, and output saturation anti-windup.
- `bench_control.c` and `.h`: ARM/PID/STOP transitions, continuous mode, and latched B1 stop.
- `main.c`, `prj.conf`: fractional PWM, B1 interrupt plus control-thread polling, telemetry, and FPU sharing.
- `bringup/motor_test/start.py`, `stop.py`, `tests/check_motor_pid.py`: detached capture, ownership publication, graceful stop, constant-memory flushed logs, and Windows state-file lock retries.
- `tests/test_velocity_control.c`, `tests/test_motor_bench.c`, `tests/test_motor_pid.py`: controller behavior, continuous operation, hold/backdrive, stop/fault handling, and host failure paths.

Host controller tests, ten diagnostic profile combinations, Python regressions, protocol tests, Nucleo build, and whitespace checks passed before commit. Local verification reports are in `logs/motor-bench/pid-host-verification/`. Temporary verification/flash/analysis scripts from this session were removed before commit; use the documented commands rather than assuming those helpers still exist.

Hardware evidence supports a first bounded 45 RPM trial and operation of the revised continuous image beyond the old four-second cap. It does not establish load rejection, long-term stability, current/thermal margins, or physical stop timing. The first continuous manual-load attempt stopped on the old right-wheel motion guard. That prompted the explicitly requested guard removal; it was not a B1 test.

All `logs/` and `build/` artifacts are local and ignored. A fresh clone will not contain the evidence captures. Runtime errors persist as `.crash.txt` and `.cleanup-crash.txt` beside the PID capture when produced; background exceptions also appear in `process.log`.

## Next work, only when requested

1. Establish current session/hardware state without silently stopping or restarting it. If B1 was pressed, verify the recorded disabled outputs and stationary counts, then document the physical result.
2. Analyze the continuous log for response to the user's manual loading. Increased PWM is not measured torque or current.
3. Tune or extend control only against the requested behavior. Ground-loaded operation, thermal/current measurements, and timing qualification remain open.
4. For integration, preserve the current CRC protocol and root layout. Pi integration, braking, servo, blinkers, current sensing, and end-to-end Lab 2 timing remain separate unfinished work.

Do not rerun powered tests during documentation, test-suite, or Git closure work. Earlier sweep authorization for checked reflashing after expected stalls is not blanket authorization to reset continuous PID.

## Suggested skills

- `diagnosing-bugs` for a reported control, telemetry, or launcher failure.
- `tdd` before firmware or host feature/fix implementation.
- `codebase-design` when defining the controller/link integration boundary.
- `research` and `ketch` for component or Zephyr primary sources; `browser-harness` for browser interaction.
- `commit` when asked to commit this handoff or subsequent changes. Push this standalone checkout, verify synchronization, and do not wait for background documentation jobs.
