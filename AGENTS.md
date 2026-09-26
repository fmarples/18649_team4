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

- `pi/`: C UDP-to-UART bridge starter. The laptop wheel proxy is external; see the handout's Appendix A for its source and setup.
- `stm32_zephyr/`: full-control application starter, **not a hardware-ready implementation**. Read `README.txt` for placeholders and `doc/STM32_PINOUT.md` for known mismatches. Its overlay does not yet implement the team's pin plan.
- `bringup/encoder_test/`: separate encoder-only Zephyr application. It excludes motor, steering, and Pi-link control. USB telemetry was verified; wheel-motion checks and calibration remain pending in its README.
- `tests/check_encoder_serial.py`: checks actual encoder telemetry. A streaming pass does not establish correct motion counting.
- `TASK_TABLE_STARTER.md`: scheduling template, not measured timing evidence.

Keep the Pi and STM32 `protocol.h` definitions consistent when changing the team-designed UART protocol. The handout does not prescribe that binary layout.

## Hardware and evidence rules

- Preserve the distinction between **team-confirmed wiring**, **planned wiring**, and **starter code**. A sheet edit or successful build does not establish that hardware was rewired or tested.
- The sheet's former motor "DIR A/B" names refer to **encoder inputs**, not L298N direction outputs. Use the corrected assignments in the pin document.
- The team chose and confirmed **external E5V power**, with **JP5 on E5V and JP1 open**; connect USB for flashing/debugging after external power is on. This supersedes the earlier 5V/U5V hookup and interim USB-only recommendation. See `doc/HARDWARE.md` for details and unverified measurements.
- For encoder-only bring-up, disconnect the L298N's 12 V motor-power feed separately from the converter branch powering the Nucleo. Change wiring only with supplies off. Before powered actuator tests, verify common ground, voltage limits, driver jumper states, inactive boot/reset outputs, and mechanical safety.
- Verify L298N braking against its truth table. Enable-low coasts; the starter's brake function is not evidence of dynamic braking.
- Flag conflicting requirements rather than silently resolving them: the handout describes 150 ms link loss in Part 2 but 100 ms at checkoff; the starter chooses 100 ms. Record the team's eventual interpretation and measured results.
- Update the relevant hardware or bring-up document when the team confirms a model, wiring change, or test result. Keep detailed pin tables in the pin document rather than duplicating them here.
