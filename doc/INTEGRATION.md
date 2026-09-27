# Integrated firmware

`main` contains one Zephyr application combining Parts 3.1-3.4 with Part 4
scheduling and instrumentation. Part 4 is not a separate replacement for the
actuator implementation: combined Part 3 tests use this same firmware.
The older motor-only commit is an archived diagnostic baseline, not required
for normal combined testing.

## Components and integration decisions

- Motor/encoder/PID implementation from `983cb1b`, combined with steering,
  blinkers and self-test in `3b04a43`.
- Existing 1320 counts/revolution, corrected forward signs, average wheel-speed
  control, 23..300 RPM active targets, 60%/200 ms startup and 40..100% running
  PWM policy retained. Motor/PID tuning was not changed by Part 4.
- Motor PWM remains on TIM3/PB4 and TIM2/PB10 at 10 kHz. Servo PWM is independently
  generated on TIM4/PB9 at 50 Hz. PA5/D13 belongs only to front-right blinker.
- One owner applies motor outputs before servicing servo and lamps. Status,
  current workqueue and USB console have lower application priorities.
- State codes: motor fault 5, self-test 6, actuator fault 7. Pi and STM32 modules
  must use the matching CRC protocol; deploy all `pi/*.py` dependencies together.
- Team steering calibration is tracked as 1200/1600/2000 us in
  `config/servo_calibration.json`; actual mechanical limits require verification
  after linkage changes.

## Fault and operating policy

A/button 0 enters self-test immediately; its double-press window is 400 ms.
Self-test and transport faults request dynamic motor braking and hazards;
LIVE steering is disabled. B1 retains the motor implementation's latched
enable-low/coast stop until reset. A peripheral output failure latches an
actuator fault. Failed output hardware cannot guarantee physical braking.

Servo starts OFF. It retains explicit calibration load, arm/LIVE commands and
a 500 ms USB heartbeat lease. Fault recovery does not automatically re-arm it.
The servo console's OFF command does not stop the motors.

## Part 4 additions

Commit `18da014` adds the priority-3 dedicated current workqueue/cache interface,
timing markers, logging and build/test support. Application priorities are
control 1, status 2, current workqueue 3 and console 4. The UART command timeout
is 60 ms; Pi UDP freshness is 80 ms. See the [task table](../PART4_TASK_TABLE.md)
for cadence, synchronization, latency targets and upstream fault distinctions.

Part 3.5 is deliberately incomplete: ADC is disabled, the backend returns
unavailable data, and no current-based control decision is implemented.
The [sensor interface](CURRENT_SENSOR_HANDOFF.md) defines the contract for
calibrated readings.

## Verification and references

The integrated image builds and software tests pass. Individual steering and
blinker operation has been reported; combined-board operation and physical
timing have not been demonstrated by these commits. See the
[software evidence](PART4_SOFTWARE_RESULTS.md), [pin map](STM32_PINOUT.md),
[hardware record](HARDWARE.md), [timing points](PART4_TIMING.md) and
[measurement worksheet](PART4_MEASUREMENTS.csv).

Firmware build output is `build/part4/zephyr/zephyr.bin`. No rollback to the
motor-only image is required to test the integrated implementation.
