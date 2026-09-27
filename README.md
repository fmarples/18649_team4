# Team 4 Lab 2

`main` contains the combined Part 3 actuator implementation and Part 4 Zephyr
scheduling. Use the current firmware for combined motor, brake, steering and
blinker testing; there is no separate Part 4 application or required rollback.
Part 3.5 is unfinished: current readings deliberately remain unavailable.

## Code

- `stm32_zephyr/`: NUCLEO-F401RE firmware, UART parsing, motor/PID control,
  steering, blinkers, self-test, scheduling, current interface and timing markers.
- `pi/`: UDP-to-UART bridge, CRC protocol and optional GPIO timing markers.
- `windows/`: wheel-proxy launcher, servo console and firmware build helper.
- `bringup/encoder_test/` and `bringup/motor_test/`: independent diagnostics.
- `tests/` and `test_protocol.py`: software and explicitly invoked hardware tests.
- `tools/`: generated-build checks, bounded QEMU runner and status-log summary.

The Part 3 integration commit is `3b04a43`; the Part 4 implementation commit is
`18da014`. The retired branches are preserved as [archive tags](doc/BRANCH_ARCHIVE.md).

## Architecture and operating policy

`Logitech wheel -> Windows proxy -> UDP 8000 -> Pi -> USART1 -> STM32 actuators`

The Pi link uses 115200 baud, 8N1. Commands carry raw wheel/pedal values and
buttons; status carries system state and current validity. Deploy matching
Pi and STM32 versions and all `pi/*.py` dependencies together.

One priority-1 owner applies motor outputs before steering and lamps. Status,
current sampling and USB diagnostics run at priorities 2, 3 and 4 respectively.
The three current channels remain unavailable until the actual ADC backend and
calibration are supplied. Current telemetry does not control actuators.

Steering starts OFF, uses the tracked 1200/1600/2000 us calibration and retains
explicit arming plus a USB heartbeat lease. Fault recovery does not re-arm it.
The servo console's OFF command does not stop motors. See the
[integration design](doc/INTEGRATION.md) and [protocol](PROTOCOL.md) for details.

## Team documentation

- [Task table and scheduling rationale](PART4_TASK_TABLE.md)
- [Hardware BOM/power record](doc/HARDWARE.md) and [pin assignments](doc/STM32_PINOUT.md)
- [Encoder calibration](doc/ENCODER_SPEC.md) and [motor characterization](doc/MOTOR_CHARACTERIZATION.md)
- [Current-sensor backend contract](doc/CURRENT_SENSOR_HANDOFF.md)
- [Timing points and measurement method](doc/PART4_TIMING.md)
- [Blank measurement worksheet](doc/PART4_MEASUREMENTS.csv)
- [Software verification record](doc/PART4_SOFTWARE_RESULTS.md)
- [Steering evidence](doc/PART3_3_RESULTS.md) and [blinker evidence](doc/PART3_4_RESULTS.md)
- [Lab 2 handout](doc/18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf)

The current integrated image builds and software tests pass. Individual steering
and blinker operation has been reported. Combined-board operation, physical
timing and real current measurements remain pending; software test results do
not certify those measurements.

## Build and software checks

From the repository root on Windows, with an installed Zephyr workspace/SDK:

```powershell
.\windows\build_part4.ps1 -ZephyrWorkspace 'C:\path\to\zephyrproject' -Sdk 'C:\path\to\zephyr-sdk'
```

This only builds and checks configuration; it does not flash or open hardware.
Output: `build/part4/zephyr/zephyr.bin`. Generic software checks in the appropriate
Python environment are:

```sh
python -m unittest discover -s tests -p "test_*.py" -v
python test_protocol.py -v
```

Native C wrappers may skip without host GCC; the ARM/QEMU suite lives in
`tests/integration/`. Build outputs and run logs are ignored by Git.
Personal operator walkthroughs and tutoring notes are maintained outside this
repository.
