# Team 4 project context

## What we are building

18-449/18-649 Lab 2: bring up a car's sensors and actuators under Zephyr on one **NUCLEO-F401RE**. The team's motor driver is an **L298N dual H-bridge module**.

Intended command path:

`Logitech wheel + pedals -> laptop proxy -> UDP port 8000 -> Raspberry Pi 4 -> UART -> Nucleo`

The Nucleo controls two DC motors using encoder feedback, one steering servo, and four blinkers; it reports three current sensors and system state to the Pi. Current readings are read-only for this lab. CAN, a second MCU, and wheel force feedback are outside Lab 2's scope. The laptop's ST-LINK USB connection is for development and serial diagnostics, separate from the intended Pi-to-MCU UART link.

## Read these before making assumptions

- **LAB 3 CAN PINOUT ERRATUM:** the handout reverses the XIAO CAN expansion board's SPI data pins. **D9 is MISO; D10 is MOSI.** Use the manufacturer-verified correction in [STM32_PINOUT.md](doc/STM32_PINOUT.md#lab-3-handout-erratum-can-module-mosimiso-are-reversed) for both Pi and Nucleo wiring. Preserve the working Pi connections. Part 0 and Part 1 are verified; read [Lab 3 bring-up results](doc/LAB3_CAN_BRINGUP.md) before further testing. During that diagnostic session, both Nucleos ran a non-actuating diagnostic with TX off at boot; `lab3 tx 2/3` starts nominal 100 ms frames and `lab3 stop` stops them. During that diagnostic session, bus labels differed: Pi can0/CE1 connects N2 CAN A to N3 CAN B; Pi can1/CE0 connects N2 CAN B to N3 CAN A. Reconcile labels before relay or fault tests. At the end of that diagnostic SPI/interrupt scope session, both boards were confirmed `tx=OFF` and a three-second Pi capture was quiet. The probed board was COM6. Measured SCK period: 1.520 us (about 658 kHz despite the 1 MHz request); one CS-low transaction: 202.5 us; receive INT-to-first-CS: 76 us; INT-low width: displayed maximum 336 us across 254 scope measurements. These are diagnostic observations, not application task WCET or proven bounds. See `doc/LAB3_CAN_BRINGUP.md` for photos and final stop logs. Both Pi CAN interfaces remain enabled at 500 kbit/s.

- **Lab 3 measurement firmware and results:** measurement-only scope, no task graph or actuator output. Read [selected timing results](doc/LAB3_TIMING_RESULTS.md), [measurement boundaries/deployment](lab3_wcet_baseline/lab3_wcet_baseline/README_WCET_BASELINE.md), and [chronological bring-up evidence](doc/LAB3_CAN_BRINGUP.md). Both boards now run the October 21 polling revision archived under `logs/lab3-can/20261021-spi-polling/`: 060412 sources with `spi-max-frequency` 10 MHz (84/16 = 5.25 MHz actual) and `CONFIG_SPI_STM32_INTERRUPT=n`. Earlier results used interrupt-mode SPI at 5.25 MHz (`20261021-spi10m-build`) or 656.25 kHz (060412). Current roles after the final October 21 pyOCD flash: N2 is ST-LINK ending 124020/COM6 (the scope-probed board); N3 is ending 171333/COM4. Rediscover ports before use. Pi can0/CE1 connects N2 B to N3 A; can1/CE0 connects N2 A to N3 B. Do not relabel historical captures. B1/PC13 replaces PA8; app-managed watchdog requires `CONFIG_WDT_DISABLE_AT_BOOT=y`. ST-LINK drivers work, but rejected readbacks are not backups; the user waived diagnostic backup. N3 reuses Lab 2 PID with synthetic 20 ms samples every 10 ms and FPU sharing; N2 reuses calibrated Lab 2 steering mapping without PWM. DRIVE remains a GPIO demo. The user delegated the SPI choice; it now requests 10 MHz (MCP2515 maximum). Distinguish the SPI clock, build, workload and boundary in every result. Probe selection and TX gating use `timing probe NAME` and `timing tx off|on`; old diagnostic `lab3 stop` does not apply. Six host measurement tests and thirteen Pi receiver/protocol/wheel/marker/CMD_TX-order tests passed. Pi latency investigation found scheduler stalls; CPU3 affinity was not adopted. FIFO priority 1 improved measured software latency and must be explicitly reapplied after process restart; this is not a PREEMPT_RT kernel installation. Never persist credentials. On October 21 the scope probes were on Nucleo 124020: CH1 PC8/CN10-2 and CH2 PB5/D4. Scope photos are published, resized with EXIF stripped, in `doc/lab3-scope/` and linked from the results doc; originals stay in ignored `logs/lab3-can/`. Pi CMD_TX now follows both CAN writes; the October 19 Pi scope results used the pre-write boundary and are superseded. Corrected Pi idle/stress scope captures IMG_0864/0865 are recorded; CPU load workers are stopped. The FIFO-1 bridge and sender keep running; use pi-scope/state.json and stop.py. GPIO markers are synchronized per drained UDP batch; the latest-packet and batch CSV events have different boundaries. The Pi rebooted after October 19; the October 21 bridge recorded in `pi-scope/state.json` replaced PIDs 1587/30956. On October 21, after a boot, N3 CAN B was latched dead until reset (see the bring-up doc); check per-bus RX/reject counts after every boot. Reset a board remotely with `pyocd reset -m hw -O connect_mode=under-reset -u <serial> -t stm32f401retx`; software reset fails with AP wait. Verify ownership and live state through `logs/lab3-can/pi-scope/state.json` and its start.py/stop.py before acting on PIDs. Remote CSV/stdout/crash paths are recorded there; MCU serial/crash logs and matching ELFs are under `logs/lab3-can/`. Keep measurement traffic running unless a necessary transition or user request requires stopping. Report measured maxima directly, record each result and advance in the same turn rather than making the user ask 'next'. Remaining hardware/relay/fault coverage is listed in the results document.

- **Requirements, timing, checkoff, or deliverables:** read the [Lab 2 handout](doc/18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf). This is the assignment source, not proof of the team's actual wiring or exact component models.
- **Wiring, GPIO, timers, UART, ADC, power, or hardware bring-up:** read [STM32 pin assignments](doc/STM32_PINOUT.md), including its proposed revisions and unresolved integration issues. Consult this before asking the user which board or pins the project uses.
- **Parts, electrical ratings, or component-specific behavior:** read the [team BOM and power setup](doc/HARDWARE.md). It supplements the handout's generic kit list. Keep confirmed parts separate from required parts and unknown models.
- **Team measurements, diagrams, and shared documents:** use the [team Google Drive folder](https://drive.google.com/drive/folders/1tPSb31DnQEuhYn843_J5W0746Dr3bdPd?usp=drive_link). The [Lab 2 Part 1 results and pin-planning sheet](https://docs.google.com/spreadsheets/d/1dooWs_u2aW8KV9ROrJsESd9B8kbxStf5QkPFaePCx2k/edit?gid=177898744#gid=177898744) holds wheel measurements and the revised pin plan. Open the relevant document before citing its contents; this repo does not mirror the whole Drive folder.
- **Building, flashing, or checking encoders on this Windows host:** read [encoder bring-up instructions](bringup/encoder_test/README.md) for installed toolchain paths, safe bench setup, commands, and verification status. Rediscover COM ports and drive letters before use.

## Code and current state

- **Starting/stopping the wheel session:** use root `start.py` / `stop.py`, not
  ad-hoc background launches. Read `doc/ONE_CLICK_START.md` for ownership, SSH
  setup and persistent logs. Start auto-connects the wheel and can cause motion;
  stop targets only the recorded GUI tree and unique Pi service. The scripts
  do not deploy Pi files or flash firmware. The user wants Python scripts only,
  without .lnk shortcuts. This laptop has passwordless SSH alias `wheelpi` with a dedicated
  local key; private key material stays outside the repo.

- **`main`:** combines the motor/PID link with Tianyi's blinkers,
  self-test and Pi-controlled steering. September 28 integration also includes
  bounded background diagnostics, 20 ms Windows wheel timers, MCU link counters
  and all three current channels. Read `doc/SESSION_2026-09-28.md` for the latest
  bench summary; transient link timeouts and current calibration remain open.
  Read `doc/INTEGRATION.md` for the integration design.
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
- `stm32_zephyr/`: CRC Pi link, encoder/PID and L298N driver with pedal cutoff, kick, braking, B1 and link-loss handling, now combined with blinkers/self-test and centered-start Pi steering. Part 3.5 ADC acquisition is implemented with nominal calibration, direct ACS712 5A connections and the user's 4.320 A upper-ADC-rail endpoint magnitude. Both motor sensors have reversed orientation: subtract output from zero; servo keeps output minus zero. Upper-rail reports are -4320 mA motors/+4320 mA servo, with no symmetric current cap. Read `doc/CURRENT_SENSOR_HANDOFF.md` before changing current conversion or testing sensors; hardware calibration/testing and physical verification of console-independent steering remain pending. This is not the old full-control starter.
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
