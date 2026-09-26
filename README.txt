LAB 2 - FULL STARTER CODE
=========================

This is a STARTER implementation for the Sensor/Actuators lab. It is meant to
be read, edited, tested, and explained by the team. It is NOT a drop-in final
solution because the handout deliberately leaves hardware pins, sensor
calibration, control gains, wheel ranges, and some design decisions to the team.

SOURCE-BASED REQUIREMENTS USED HERE
------------------------------------
- Pi sends a command to STM32 on every UDP state update and at least every 50 ms.
- STM32 sends a status frame every 20 ms +/-10% with three current readings and
  zone state.
- Invalid/out-of-range command frames are rejected.
- The handout states three missed command updates / 150 ms means fail-safe.
- The checkoff separately asks for link-loss fail-safe within 100 ms. This starter
  uses 100 ms; discuss/document the choice with your team.
- Motor velocity control uses the average of the two encoder velocities.
- Brake disables PWM and uses dynamic braking; brake has priority over throttle.
- Steering maps the cockpit wheel angle to the mechanical steering range.
- Blinkers: 1 Hz +/-10%, 50% duty; one side cancels the other; steering threshold
  return self-cancels; error state hazards are 2 Hz.
- Current sensors are read-only and reported in the status frame.
- Zephyr is used for priority-based preemptive scheduling.

FILES
-----
stm32_zephyr/src/
  main.c              - task/thread integration
  uart_link.c/.h      - UART parser/transmitter
  protocol.h          - shared UART frame definitions
  app_state.h         - command/system state types
  motor.c/.h          - H-bridge PWM/direction/brake starter
  encoder.c/.h        - encoder counter/velocity starter
  pid.c/.h            - generic PID calculation
  drive_control.c/.h  - throttle -> target velocity -> motor command
  steering.c/.h       - wheel value -> servo PWM mapping
  blinker.c/.h        - turn signal/hazard state logic
  current_sensor.c/.h - ADC/current conversion starter
  safety.c/.h         - error state + link timeout
  self_test.c/.h      - wheel-button self-test starter
  status.c/.h         - 20 ms status frame

WHAT YOU MUST EDIT BEFORE HARDWARE TESTING
------------------------------------------
1. BOARD / DEVICETREE
   Edit app.overlay for your EXACT STM32/Nucleo board. Identify the UART,
   UART TX/RX pins, PWM channels, GPIO pins, and ADC channels.

2. UART
   Confirm 115200 8-N-1 on both ends. Confirm the physical connection is:
     Pi TX -> STM32 RX
     Pi RX -> STM32 TX
     common GND
   Do not connect incompatible voltage levels. The handout specifically warns
   that Raspberry Pi GPIO is 3.3 V and not 5 V tolerant.

3. WHEEL RAW RANGES
   Record the actual lX/lY/lRz values from Part 1 and replace the placeholder
   validation limits in uart_link.c. Decide whether Pi or STM32 performs scaling.

4. BUTTON INDICES
   Replace LEFT_BUTTON, RIGHT_BUTTON, and SELF_TEST_BUTTON with the indices you
   actually recorded from your wheel/proxy.

5. MOTOR DRIVER
   motor.c contains example GPIO/PWM behavior only. Verify the L298N/H-bridge
   truth table and wiring. In particular, verify the dynamic-braking state before
   connecting motors.

6. ENCODERS
   Implement the actual encoder interrupts/inputs. Replace COUNTS_PER_REV and
   WHEEL_CIRCUMFERENCE_M with measured values. Verify direction for both wheels.

7. PID
   Tune kp/ki/kd experimentally. The values in drive_control.c are placeholders.

8. STEERING SERVO
   Measure/verify the servo PWM period and safe pulse-width endpoints. Replace
   the placeholder 1000-2000 us range if your servo requires something else.
   Never use the MCU GPIO to power the servo.

9. BLINKERS
   Replace the four GPIO aliases and confirm LED polarity. Confirm the steering
   threshold against your team's documented value.

10. CURRENT SENSORS
    Configure the ADC channels and implement the sensor's voltage/current transfer
    function. The current starter returns raw ADC counts as a placeholder.

11. SELF TEST
    The starter provides a simple toggle. The checkoff asks for single-press
    error/hazards/brake and double-press recovery, so add your team's debounce and
    double-press timing behavior.

12. TEST POINTS
    Add GPIO toggles for CMD_RX, PWM_SET, PWM_OUT, DIR_A, SRV, FL/FR/RL/RR if
    required by your wiring/instrumentation. Keep instrumentation out of timing-
    critical paths where possible.

13. TASK PRIORITIES / PERIODS
    The example uses a 2 ms control thread and a 20 ms heartbeat. These are starter
    values, not a claim that every task is optimally scheduled. Build your task table
    from the actual implementation and your measured deadlines.

IMPORTANT DESIGN NOTE
----------------------
The UART protocol is a team-designed binary protocol. The lab handout recommends
UART but does not prescribe this exact byte layout. Keep protocol.h identical on the
Pi and STM32, and document the final protocol in your write-up.

The simple additive checksum is intentionally easy to understand. Your team can
replace it with CRC if you decide that is more appropriate.

BUILD ORDER
-----------
1. Get the Nucleo blinky/build working with Zephyr.
2. Configure only UART and prove CMD_RX works.
3. Add steering and verify servo range with wheels off the ground / linkage safe.
4. Add encoders and verify counts/direction.
5. Add motors/PID with the chassis safely supported.
6. Add brake/dynamic braking and verify the H-bridge truth table.
7. Add blinkers and self-test.
8. Add current sensors/status reporting.
9. Perform link-loss and malformed-frame tests.
10. Add/verify scope test points and timing measurements.

SAFETY
------
Do not power a motor or servo from an MCU GPIO. Verify power rails, common
reference/ground, polarity, pin voltage limits, and H-bridge behavior before
connecting the hardware. The lab handout specifically warns about these hazards.
