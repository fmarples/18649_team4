# Part 3.3 preparation and evidence

Date: 2026-09-26. Branch `lab2-tianyi-steering`.
Target: Tianyi's separate NUCLEO-F401RE, ST-LINK serial
`066BFF485270535067124020`. This is not the motor teammate's board.

Power inventory update: Tianyi confirms a second HW-688 converter is available.
This confirms availability of another converter, not suitability for a 6 V
servo rail. Subsequent source checking found HW-688 listings for fixed 5/5.2 V
outputs. The earlier instruction to adjust it to 6 V was premature. Subsequent
user photos confirm fixed nominal 5 V output, VIN+/VIN- and 5V/GND terminals,
and no adjustment potentiometer. An Extech MN35 meter is available with leads
already in COM and V/ohm/mA/Temp. Actual output/current measurements remain
pending. The first converter remains the STM32's 5 V source. Tianyi subsequently
reports the TA said to use 5 V and that it will work: the selected bench plan
now uses the second fixed-output converter for the servo. This guidance does
not change the published 6–8.4 V specification or establish a measured success
at 5 V. See `HW688_OUTPUT_CHECK.md`.

## Implemented

- PB9/D14 TIM4_CH4, 20 ms period, 1 us timer ticks; zero pulse at boot.
- Explicit ARM and bounded 25/5 us manual steps, operator-marked left/center/right.
- Piecewise monotonic raw-wheel mapping, including reversed servo orientation.
- No default mechanical calibration. Invalid/missing values prevent live mode.
- Live activation requires a healthy Pi link and a centered Logitech wheel.
- Self-test or lost live link disables PWM; recovery does not auto-arm.
- USB heartbeat expires after 500 ms; manual calibration can operate without Pi.
- Windows console locates the specific bench board and saves measured values to JSON.
- Corrected startup hazards and G920 A single/double-press self-test included.

## Not established by code or a successful flash

- Actual installed servo marking, second converter's measured output and current capability.
- Safe mechanical endpoints, straight-ahead pulse, physical steering direction.
- Recognition of the board's 3.3 V PWM logic by the actual servo.
- PWM period/pulse accuracy, end-to-end response <=50 ms, or integrated load timing.
- Motor braking, current-sensor readings, or complete vehicle integration.

The handout's physical tests and measurements remain required. No endpoint
numbers have been guessed or stored as team calibration. The status frames
do not contain a measured servo angle.

## Verification completed on this host

- Zephyr F401RE build passed: 40,152 bytes flash, 10,048 bytes RAM.
- 27 actual C tests passed in QEMU: 12 blinker, 8 self-test, 7 servo tests.
  The servo suite checks all 65,536 raw steering inputs for both orientations,
  endpoints/center, invalid calibration, command interlocks, lease expiry,
  link/self-test disable and no automatic resumption.
- Python: 7 protocol, 2 calibration-file/response, and 1 Windows launcher test
  passed. No real servo movement was used for these tests.
- Programmed only adapter `066BFF485270535067124020`; OpenOCD **Verified OK**.
- COM11 was initially occupied. After the user closed its serial monitor,
  captured boot output shows `PART3.3 ... boot DISABLED` and startup
  `blink=HAZARD`, alternating requested L/R values together. No init error.
- Exercised the actual Windows console transport on COM11: OFF and STATUS
  return mode 0, pulse 0, all calibration fields 0. LIVE without calibration,
  STEP/MARK while off, and invalid LOAD geometry were correctly rejected.
  No ARM command or nonzero PWM request was sent by the agent.
- Image SHA-256:
  `e89cc78b0944f545059076869997ddc5f9212af08e2da40b5cf556bad1e25f07`.
- Local raw logs: `logs/part3_3/flash.txt`, `boot-console.txt`, `core-tests.txt`,
  `disabled-console-check.txt`. A debug-register read made during attachment
  returned reset-state zeros; it is not evidence of a measured PWM waveform.
- No new files were copied onto the Pi: SSH requires the user's interactive
  password. The guide includes the one-time decoder-copy command.
