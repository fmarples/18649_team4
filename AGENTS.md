# Team 4 project context

## What we are building

18-449/18-649 Lab 2: bring up a car's sensors and actuators under Zephyr on one **NUCLEO-F401RE**. The team's motor driver is an **L298N dual H-bridge module**.

Intended command path:

`Logitech wheel + pedals -> laptop proxy -> UDP port 8000 -> Raspberry Pi 4 -> UART -> Nucleo`

The Nucleo controls two DC motors using encoder feedback, one steering servo, and four blinkers; it reports three current sensors and system state to the Pi. Current readings are read-only for this lab. CAN, a second MCU, and wheel force feedback are outside Lab 2's scope. The laptop's ST-LINK USB connection is for development and serial diagnostics, separate from the intended Pi-to-MCU UART link.

## Read these before making assumptions

- **Requirements, timing, checkoff, or deliverables:** read the [Lab 2 handout](doc/18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf). This is the assignment source, not proof of the team's actual wiring or exact component models.
- **Wiring, GPIO, timers, UART, ADC, power, or hardware bring-up:** read [STM32 pin assignments](doc/STM32_PINOUT.md), including its proposed revisions and unresolved integration issues. Consult this before asking the user which board or pins the project uses.
- **Parts, electrical ratings, or component-specific behavior:** read the [team BOM and power setup](doc/HARDWARE.md). It supplements the handout's generic kit list. Keep confirmed parts separate from required parts and unknown models.
- **Team measurements, diagrams, and shared documents:** use the [team Google Drive folder](https://drive.google.com/drive/folders/1tPSb31DnQEuhYn843_J5W0746Dr3bdPd?usp=drive_link). The [Lab 2 Part 1 results and pin-planning sheet](https://docs.google.com/spreadsheets/d/1dooWs_u2aW8KV9ROrJsESd9B8kbxStf5QkPFaePCx2k/edit?gid=177898744#gid=177898744) holds wheel measurements and the revised pin plan. Open the relevant document before citing its contents; this repo does not mirror the whole Drive folder.
- **Building, flashing, or checking encoders on this Windows host:** read [encoder bring-up instructions](bringup/encoder_test/README.md) for installed toolchain paths, safe bench setup, commands, and verification status. Rediscover COM ports and drive letters before use.

## Code and current state

- **`main`:** combines the motor/PID link with Tianyi's blinkers,
  self-test and Pi-controlled steering. Read `doc/INTEGRATION.md` first.
  State 5 remains motor fault; self-test is 6 and actuator fault is 7. PA5 is
  exclusively the front-right blinker. TIM2/PB10 must remain enabled for the
  right motor; TIM4/PB9 drives steering. `config/servo_calibration.json` contains
  user-selected 1200/1600/2000 us. Tianyi now reports Parts 3.3 and 3.4 tested
  individually; exact mechanical/timing captures have not been supplied.
  The user replaced the explicit-arm/USB-heartbeat vehicle policy: boot and
  link/fault recovery wait for healthy Pi commands and a centered wheel before
  LIVE steering. Firmware embeds the tracked calibration; USB is optional.
  Manual calibration retains its heartbeat; explicit OFF stays off until AUTO
  or manual ARM/LIVE. See PROTOCOL.md. The new policy is host-tested, built and
  user-authorized flashed to ST-LINK ending 171333. Read-only status confirmed
  LIVE without USB keepalives; the user confirmed steering and blinkers work
  together. Physical cable-removal/recovery and timing checks remain pending.
  See doc/STEERING_AUTONOMOUS.md for deployment evidence and logs.

- **Branch cleanup:** integration was promoted to main, then all five old branches
  were archived as tags and deleted at the user's request. See
  `doc/BRANCH_ARCHIVE.md` for exact tips and recovery. Use the
  `18649_team4_integration` worktree on main; the original and blinker worktrees
  retain their old files at detached archived commits. Do not mistake them for
  current main or recreate old branch names merely to follow historical docs.

- **Agreed layout:** `pi/`, `stm32_zephyr/`, and `windows/` live at the repository root, not in lab/member subfolders. Tianyi agreed to this layout. Preserve his newer link implementation rather than restoring the old starter from Git history.
- `pi/`: Python UDP-to-UART bridge and CRC-based protocol. Read `README.md` for run/build commands and logs. The course wheel proxy is external; `windows/` launches it.
- `stm32_zephyr/`: CRC Pi link, encoder/PID and L298N driver with pedal cutoff, kick, braking, B1 and link-loss handling, now combined with blinkers/self-test and centered-start Pi steering. Part 3.5 ADC acquisition is implemented with nominal calibration, direct ACS712 5A connections and the user's +4320 mA reporting ceiling. Read `doc/CURRENT_SENSOR_HANDOFF.md` before changing current conversion or testing sensors; hardware calibration/testing and physical verification of console-independent steering remain pending. This is not the old full-control starter.
- `bringup/encoder_test/`: independent encoder diagnostic. Both hand-turn tests passed; left raw counts decrease forward and right raw counts increase. Use the user-validated **1320 counts/wheel revolution**. For the completed 100%-duty count/time measurement, read `doc/MOTOR_CHARACTERIZATION.md`; the user selected **300 RPM at full throttle** and a low-pedal cutoff based on measured 40%-duty speed. See `PROTOCOL.md` for the implemented target/output policy and pending hardware verification.
- `test_protocol.py`: host protocol/bridge tests. `tests/test_windows_launcher.py`: relocated Windows launcher check. `tests/check_encoder_serial.py`: hardware telemetry check.
- `PART4_TASK_TABLE.md` describes the actual implementation: owner 1, status 2, dedicated current-sampling workqueue 3, console 4. Current acquisition uses ADC1 with read-only status reporting; failed/stale samples are unavailable. PC2/CN7-35 and PC3/CN7-37 are newly allocated timing outputs; Pi trace uses BCM17/27 only with `--trace-gpio`. Follow `doc/PART4_TIMING.md`; hardware timing is unmeasured.

- **Documentation preference:** personal step-by-step operating instructions,
  tutoring explanations and host-specific session plans must stay outside the
  repository and must not be pushed to GitHub unless explicitly requested.
  Keep team code, technical specifications, task tables and verification records
  in Git. An ignored `.local-notes/` directory may point to local personal guides.

For UART changes, read `PROTOCOL.md` and update `pi/part2_protocol.py`, the encoder/decoder in `stm32_zephyr/src/main.c`, and host tests together. The old additive-checksum protocol is incompatible; no shared `protocol.h` remains in the current app.

## Hardware and evidence rules

- **Operating limits need a source:** add caps, cutoffs or restrictions only when required by the lab handout, the confirmed component's datasheet, or an explicit user request. Record that source. Do not substitute an agent-chosen precaution for the requested behavior.
- **Motor PID decisions:** the user explicitly wants continuous operation until Nucleo B1/STOP, no PID run timer or stall/reversal cutoff, and full PWM authority while retaining the measured startup/sustaining thresholds. Read `bringup/motor_test/README.md` for the current implementation and logs before changing or running it. Startup/holding diagnostic modes have separate behavior.
- Preserve the distinction between **team-confirmed wiring**, **planned wiring**, and **starter code**. A sheet edit or successful build does not establish that hardware was rewired or tested.
- The sheet's former motor "DIR A/B" names refer to **encoder inputs**, not L298N direction outputs. Use the corrected assignments in the pin document.
- The team chose and confirmed **external E5V power**, with **JP5 on E5V and JP1 open**; connect USB for flashing/debugging after external power is on. This supersedes the earlier 5V/U5V hookup and interim USB-only recommendation. See `doc/HARDWARE.md` for details and unverified measurements.
- For encoder-only bring-up, disconnect the L298N's 12 V motor-power feed separately from the converter branch powering the Nucleo. Change wiring only with supplies off. Before powered actuator tests, verify common ground, voltage limits, driver jumper states, post-initialization inactive outputs, and mechanical safety.
- **Motor-bench flashing:** the user explicitly accepts unexpected wheel motion during flashing/reset on the raised-wheel bench. Motor power may remain connected for an authorized flash; do not require disconnection solely to prevent reset/startup motion or ask for this acceptance again. This supersedes earlier isolation-before-flash instructions, not power-off wiring changes or motor isolation for hand-turn tests. Boot/reset inactivity remains unverified. Verify the flashed profile and idle outputs before the requested powered test; this is not permission to interrupt an unrelated continuous run.
- Verify L298N braking against its truth table. Enable-low coasts; the integrated driver's enable-high/equal-input braking follows the truth table but is not physically tested yet.
- Flag conflicting requirements: link loss is 150 ms in Part 2 but 100 ms at checkoff; self-test is 10 ms in the requirements table but 100 ms at checkoff. MCU timeout is now 60 ms (three missed 20 ms command updates, explicitly required by the handout); Pi still sends a brake frame after 80 ms of stale UDP. The brake frame is not an error/hazard command: upstream UDP-loss hazards wait for the additional MCU timeout. No <=100 ms upstream-UDP-to-hazards result is claimed. See `PART4_TASK_TABLE.md` and distinguish this from UART cable loss.
- Update the relevant hardware or bring-up document when the team confirms a model, wiring change, or test result. Keep detailed pin tables in the pin document rather than duplicating them here.
