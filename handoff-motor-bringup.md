# Handoff: motor bring-up and next velocity-control work

## Continuation update, 2026-09-27

Startup/holding characterization is complete. **The user superseded separate-wheel
tests with both motors together**, retaining raised wheels, 10 kHz PWM, 200 ms
startup kicks and up to four-second holds. Units remain RPM and ms/s. They requested
one-command automation and explicitly authorized checked reflashing after expected
stall faults, without retrying failed duties. Reverse/HAL/encoder/reset faults
still abort; no guard was weakened and no firmware fault-clear command was added.

`tests/run_motor_sweep.py --port COM4 --drive D --run --allow-stall-reset` completed
12 simultaneous trials. Startup: 55% passed 3/3, 50% failed. After a 60% / 200 ms
kick, 40% holding passed 3/3 for four seconds, 35% stalled the left motor and stopped
both. These are lowest tested passing values, not exact or loaded-operation minima.
See `doc/MOTOR_CHARACTERIZATION.md` for per-wheel and average RPM, preliminary
single-wheel history, limitations and captures. Full batch summary:
`logs/motor-bench/sweep-20260927-044102/summary.json`, status COMPLETE.

Final flashed profile: startup 60% / 200 ms; HOLD commands kick at 60% / 200 ms
then hold at 55% / maximum 4000 ms. Final reflash was verified idle only; both
outputs disabled, encoders stationary, fault zero. Build variables are
`MOTOR_TEST_DUTY=60`, `MOTOR_HOLD_DUTY=55`, `MOTOR_HOLD_MS=4000`. A fresh CMake build
defaults hold duration to 2000, so pass 4000 explicitly for this profile.

The firmware remains a separate bench diagnostic. No closed-loop velocity control
or Part 2 integration was added. Ground load, long-term holding, current and
thermal margins remain unverified. No powered trial is pending. See Git history for the continuation commit.
The original handoff below describes the earlier five-second profile.

## Session endpoint

The user requested a handoff after asking for current progress. No new powered trial is pending or authorized by this handoff itself. Recommended next work is to diagnose low-duty startup behavior, then implement encoder-based velocity control. Do not treat the existing bench diagnostic as completed Lab 2 motor control.

Repository was clean and synchronized on `main` at **`058f66d` — `feat: add guarded motor bring-up and encoder verification`** immediately before this document was created. The commit is pushed to `origin/main`. This handoff is a new, uncommitted file.

## Read these artifacts instead of reconstructing the session

- `AGENTS.md`: repository context, authoritative sources, hardware evidence rules.
- `bringup/motor_test/README.md`: **current flashed profile**, command protocol, chronological diagnostic results, test commands, captures, and safety limitations. Its opening sections describe current behavior; later bullets include superseded experimental configurations.
- `doc/STM32_PINOUT.md`: actual signal mapping and verified forward motor polarities. Encoder A/B pins are not H-bridge direction outputs.
- `doc/HARDWARE.md`: confirmed power setup, supply rating, jumper states, measurements, and unresolved electrical limits.
- `doc/ENCODER_SPEC.md`: measured calibration, wheel dimensions, encoder direction conventions, conflicting vendor specifications, and powered-test evidence.
- `bringup/encoder_test/README.md`: installed Windows/Zephyr tooling, environment setup, flashing and encoder-check instructions.
- `doc/18-449_649 Lab2 - Sensors and Actuators v1_0.pdf`: assignment requirements, especially section 3.1.
- `PART4_START_HERE.md`, `PART4_TASK_TABLE.md`, and `PROTOCOL.md`: integration/scheduling plan and current Part 2 protocol.
- Commit `058f66d`: implementation and test changes. Root `stm32_zephyr/` remains the team's link-only application; do not resurrect the obsolete full-control starter.

## Operational state at handoff

- The Nucleo last ran the separate `bringup/motor_test` image. Only one firmware image runs on this board; this replaces, rather than concurrently supplements, the Part 2 link application.
- Last verification showed both outputs disabled and stationary encoder counts. **Recheck physical/serial state before future actuation; a handoff cannot guarantee that hardware remains unchanged.**
- One simultaneous five-second forward trial passed. Afterwards, a console/control-priority issue was corrected, rebuilt, flashed, and checked **idle only**. Do not describe the final priority-corrected image as having repeated that powered trial.
- The current firmware accepts explicit ARM followed by LEFT, RIGHT, or BOTH. Those commands are longer forward trials now, **not the earlier 200 ms kicks**. Consult its README before using any actuation script.
- The software motion guard is not current limiting, dynamic braking, or an independent hardware cutoff. Physical induced-stall protection latency has not been validated.
- Last observed interfaces were COM4 and drive D: labeled `NOD_F401RE`. Rediscover both before use. Mass-storage flashing and console serial work; the missing ST-LINK debug driver was not repaired.
- Toolchain paths and build invocation are documented in the bring-up READMEs. The Zephyr workspace is under the local user's home directory, using its `.venv`; SDK version is recorded there. Avoid depending on a specific account name.
- Local `build/` and `logs/` remain ignored and must stay untracked. Detailed captures are under `logs/motor-bench/`; they are local evidence, not files guaranteed to exist in a fresh clone.

## What the next investigation must distinguish

The unresolved issue is **low-duty startup**, not whether either motor can turn or which direction is forward. The measurement sequence and exact values are already in the motor-test README.

Important interpretation limits:

- The successful unloaded DC measurement and earlier loaded low-duty measurement changed **both load and duty**. They do not independently prove a defective bridge.
- The user saw no obvious input-supply dip, but the multimeter has no MIN/MAX capture and may miss short transients. Supply sag was not conclusively excluded.
- A lower PWM-frequency comparison was proposed but **never implemented or run**. Do not report it as a failed or successful experiment.
- Full-duty rotation and a short dual-motor run do not establish acceptable startup current, thermal margins, or ground-loaded performance.
- Encoder counts captured after output disable include coast-down. Do not divide a run-plus-coast total by the powered interval and call it measured velocity.

Candidate next steps, not commitments:

1. Read the recorded evidence and select one discriminating low-duty/PWM experiment. Keep duty, duration, loading, and frequency changes explicit rather than changing several at once. Verify L298N enable-PWM/decay behavior against primary documentation if using it to explain the symptom.
2. Maintain bounded commands and explicit reporting of any motion-guard abort; do not silently retry or raise duty. Existing guarded firmware may abort low-duty experiments before a slow meter can provide a useful reading.
3. Once startup and speed response are understood, add timestamped velocity measurement and a documented throttle-to-target-speed mapping, then closed-loop control. Use the calibration and sign conventions in `doc/ENCODER_SPEC.md`; do not re-adopt the vendor's contradictory nominal count.
4. Integrate only after respecting the current CRC protocol and the separate link application. Servo, blinkers, current sensors, braking, and complete system validation remain unfinished.

## Working style and practical lessons

- The user wants the assistant to perform software installation, editing, builds, flashing, serial operations, and documentation directly. Ask the user only for physical observations/actions or genuine decisions the tools cannot resolve.
- Proceed in clear steps and announce powered trials immediately before they occur. Avoid repeatedly asking for already-established wiring or safety confirmations unless conditions change.
- The user previously accepted startup-motion risk with raised wheels and preferred flashing without repeatedly isolating motor power. This is **not** evidence that reset behavior is electrically safe or blanket authorization for arbitrary future trials.
- Physical equipment available was the shared wall adapter and a basic multimeter, not a current-limited bench supply. The user performed measurements when given precise terminals and meter mode.
- Encoder telemetry resolved direction more reliably than asking the user to judge brief movement by eye. Preserve this feedback loop.
- A transient Windows drive-access error occurred immediately after one flash; a later drive recheck succeeded. Require both a clean flash result and the expected runtime banner before actuation, rather than trusting a file copy alone.
- Keep safety claims qualified: software-disabled outputs do not mean the wheel has mechanically stopped, and successful telemetry is not a waveform/current measurement.

## Verification and closure

Host motor-control tests, existing Python tests, PWM configuration checks, and whitespace checks passed before commit. Hardware results and the distinction between tested revisions are recorded in the bring-up README. Do not rerun hardware actuation as an incidental part of a general test or commit workflow.

For future git closure, the user uses the `commit` skill: inspect all changes, stage exact non-secret paths, review, commit, and push this standalone checkout. Do not wait for or repair background documentation jobs.

## Suggested skills

- **diagnosing-bugs**: continue the evidence-driven low-duty investigation with a reproducible, bounded feedback loop.
- **tdd**: before firmware features or fixes; existing command/output tests and serial entry points provide established seams.
- **codebase-design**: if defining the velocity-controller/driver boundary or preparing Part 2 integration, rather than growing the bench app into the final controller ad hoc.
- **research** and **ketch**: for primary L298N/Zephyr documentation or PWM/decay questions. Use **browser-harness** for browser interaction, particularly authenticated shared documents.
- **commit**: when the user requests committing/pushing subsequent changes.
