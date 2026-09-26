# Pi-to-STM32 motor link

The root application now connects validated CRC commands to the encoder/PID
motor driver on the NUCLEO-F401RE. It is not a complete Lab 2 vehicle controller:
servo, lamps, current sensing and wheel-button self-test remain pending.
This integration is built and host-tested, **not flashed or hardware-validated**.
The user deferred the Pi end-to-end test.

## Wiring and transport

115200 baud, 8 data bits, no parity, 1 stop bit, no hardware flow control.
All signal levels are 3.3 V. TX crosses to RX and ground is shared.

| Pi 4 physical header pin | Function | Nucleo Arduino header label |
| --- | --- | --- |
| 8 / GPIO14 | Pi TX | D2 / PA10 / USART1 RX |
| 10 / GPIO15 | Pi RX | D8 / PA9 / USART1 TX |
| 6 | Ground | GND |

The Pi uses its own USB-C supply. The Nucleo uses external E5V power with
ST-LINK USB for flashing/debugging; follow [the power setup](doc/HARDWARE.md#current-power-setup)
and apply external power before USB. No 5 V or 3.3 V power-rail wire goes between
the Pi and Nucleo. USART2 PA2/PA3 remains the laptop console, independent of USART1.
Sources: local Zephyr Nucleo-F401RE connector DTS; ST UM1724;
https://www.st.com/resource/en/user_manual/dm00105823.pdf
https://www.raspberrypi.com/documentation/computers/configuration.html#configure-uarts

## Command: 28 bytes, Pi to STM32

All multibyte integers are little endian. No C struct layout is sent directly.

| Byte offset | Size | Meaning |
| --- | --- | --- |
| 0 | 2 | ASCII L2, frame marker |
| 2 | 1 | Protocol version 1 |
| 3 | 1 | Type 1 = command |
| 4 | 4 | Unsigned UART command sequence number |
| 8 | 4 | Signed steering raw counts, -32768 through 32767 |
| 12 | 4 | Signed throttle raw counts, -32768 through 32767 |
| 16 | 4 | Signed brake raw counts, -32768 through 32767 |
| 20 | 4 | Button bitmask, bits 0 through 10; other bits must be zero |
| 24 | 4 | CRC-32/IEEE of bytes 0 through 23 |

Python zlib.crc32 and Zephyr crc32_ieee use the same CRC convention.
Button bit n represents Part 1's zero-based raw index n. No vehicle-function
assignment is implied. Pedals are 32767 released and -32768 fully pressed.

## Motor control

The user selected **300 RPM at full throttle** and a low-pedal cutoff based
on the measured 40%-duty sustaining speed. `stm32_zephyr/src/throttle_mapping.c` implements
the conversion after frame validation, without changing the raw-pedal packet:

```text
linear_rpm = (32767 - throttle_raw) * 300.0 / 65535.0
if brake_raw != 32767 or linear_rpm < 23:
    target_rpm = 0
else:
    target_rpm = linear_rpm
```

The **23 RPM** initial threshold is the mean from three simultaneous 40%-duty
holds in [the measurement record](doc/MOTOR_CHARACTERIZATION.md). Some slowing
remained in those short trials, so this is not a newly verified steady or loaded
minimum. The cutoff is approximately **7.67% pedal travel**. With integer raw
inputs, raw **27743 and higher** requests STOP; raw **27742 and lower** requests
at least 23 RPM, provided the brake is fully released. Half pedal remains about
150 RPM; full pedal remains 300 RPM. The implementation retains milli-RPM
precision. It never requests a positive speed below the sustaining threshold.

The main thread passes this target to `drive_control.c` and `motor_driver.c`.
They reuse the bench's encoder decoder and PID with **1320 counts/revolution**,
left-negative/right-positive forward signs, and equal duty to both motors.
Every stopped-to-driving transition gets **60% for 200 ms**, then PID with
**40..100% PWM authority**. Moving pedal updates retain PID history and do not
restart the kick. A new target updates the proportional output immediately;
encoder feedback remains on the existing 20 ms actual-dt schedule. The kick
ends at its deadline even between encoder samples.

- Below-cutoff/released throttle: zero duty, coast.
- Brake pedal, startup without a link, invalid command or link timeout:
  dynamic braking, IN1..4 low and both enables held high.
- B1 or real encoder/GPIO/PID faults: latch propulsion off until reset.
  B1 disables both enables and coasts; releasing it cannot restart.
- HAL errors attempt GPIO-low enables and latch a fault. A failed HAL is not
  proof of a successful physical stop.

Braking follows [ST L298 DS0218 Rev 5, Table 5](https://www.st.com/resource/en/datasheet/l298.pdf):
enable-high with equal inputs is fast stop; enable-low is coast. Dynamic braking
is a constant enable level, not propulsive PWM. Its physical performance is
still untested here. No stall/reversal timer or run-duration limit was added
to PID. Current and thermal protection remain absent.

USB diagnostics print `DRIVE` mode (0 coast, 1 forward, 2 brake), target and
measured milli-RPM, milli-percent duty, raw counts, MCU sample time and fault.
Faults are 1 B1, 2 sensor/GPIO, 3 PID data, or negative HAL codes. The binary
status layout remains unchanged. Bench ASCII ARM/PID/STOP commands are not
accepted by this application; use Pi brake/release commands or local B1.

## Status: 56 bytes, STM32 to Pi

| Byte offset | Size | Meaning |
| --- | --- | --- |
| 0, 2, 3 | 2, 1, 1 | L2, version 1, type 2 |
| 4 | 4 | Unsigned status sequence |
| 8 | 4 | STM32 uptime in milliseconds, wraps modulo 2^32 |
| 12 | 4 | Last accepted command sequence |
| 16 | 4 | State: 0 WAITING, 1 LINK_OK, 2 timeout, 3 bad input, 4 overflow, 5 motor fault |
| 20, 24, 28 | 4 each | Current accepted/safe steering, throttle, brake values |
| 32, 36, 40 | 4 each | Signed left-motor, right-motor, servo current in mA |
| 44 | 4 | Current validity mask: bits 0, 1, 2 correspond to these sensors |
| 48 | 4 | Rejected-frame/overflow counter |
| 52 | 4 | CRC-32/IEEE of bytes 0 through 51 |

Current values are INT32_MIN and validity is zero in this starter, because no
sensors are wired. These are unavailable readings, NOT measured 0 mA. Replace
them with calibrated readings after the sensors are connected. The state enum
describes link state plus a latched motor fault; full vehicle zone state remains pending.

## Timing and failure behavior

- Pi forwards each newly received, valid, advancing wheel UDP packet.
- Between UDP updates, Pi refreshes the latest state about every 20 ms.
- After 80 ms without fresh valid UDP, Pi sends one released-throttle/full-brake
  frame, then pauses commands. It drains queued UDP before recovery so an expired
  backlog cannot immediately undo the stop. Duplicate/backward counters do not
  refresh input. A new sequence baseline is allowed only after input timeout.
  Invalid UDP also sends a brake frame and pauses; it preserves the previous
  valid counter/time until a real timeout.
- STM32 checks for command timeout every roughly 1 ms and enters its link
  error state at 80 ms since the last accepted frame's reception time.
- A periodic Zephyr timer requests status every 20 ms. Actual wire timing
  must be measured; successful compilation does not prove the +/-10% limit.
- The handout says 150 ms in Part 2 and 100 ms in final checkoff. The 80 ms
  timeout targets the stricter checkoff with margin; confirm the conflict
  with the TA. This is a proposed implementation setting, not a measured result.
- The explicit upstream brake avoids waiting for both freshness and MCU timeout
  before stopping. The 80 ms budgets target the stricter 100 ms requirement,
  but Python/OS scheduling, UART transmission and output latency still need
  measurement. A crashed Pi bridge is handled by the MCU's 80 ms timeout.
- Bad CRC/range/button masks cannot update control values or refresh the
  timeout. Invalid complete candidates set ERROR_BAD_INPUT. Header noise or
  incomplete frames are ignored and eventually time out. A valid later frame
  restores LINK_OK. A corrupt/truncated candidate can consume part of the next
  frame; the parser recovers at a subsequent complete L2/version/type header.
- UART ISR gathers candidates into an eight-frame queue. On overflow it
  discards the backlog and sets a fault instead of applying old queued inputs.
  Already queued packets older than the timeout are rejected.
- Duplicate/old UART sequence numbers while LINK_OK do not refresh the timer.
  After error/timeout, a valid frame establishes a new sequence baseline.
- Safe internal values are steering 0, throttle 32767, brake -32768, target zero.
  The motor owner applies the stop policy above. Hazards and servo remain absent.
  Fresh valid commands recover ordinary link errors, but never clear B1 or a
  latched motor fault.

## Thread responsibilities

| Context | Responsibility |
| --- | --- |
| UART ISR | Collect candidate frames; timestamp completion; enqueue |
| Main, priority 1 | Validate commands; timeout; read encoders/B1; own PID and all motor writes; update LED |
| Status, priority 2 | Transmit one binary status after each 20 ms timer event |
| Console, priority 3 | Human-readable USB prints approximately every 250 ms |

Lower Zephyr priority numbers here have higher scheduling priority. Console
prints are throttled so debugging does not define the link's heartbeat rate.
The console's 250 ms print interval is not a link-loss timing measurement.

## Files and validation

- stm32_zephyr/: root application; the integration was built in `build/pi-motor/`.
- pi/part2_bridge.py and pi/part2_protocol.py: copy both into ~/18649/part2.
- test_protocol.py: host tests for layout, CRC, raw axes/button extraction,
  stream resynchronization, sequence wrap, and stopping stale UDP refreshes.
- `tests/test_drive_control.c` checks cutoff/kick/PID/stop behavior; the shared
  bench controller tests remain in place. Protocol/freshness tests cover frame
  compatibility, paused input, queued stale input and sequence protection.
- Build/test logs: `logs/motor-integration/`; host preparation exceptions:
  `logs/motor-integration/verify.crash.txt` when produced. On hardware, capture
  the ST-LINK console to `logs/motor-integration/console-<timestamp>.log` for
  diagnostics and MCU fatal traces; no native MCU crash dump is configured.
- No integrated image was flashed, no Pi deployment was made, and the user
  deferred the full end-to-end run. 2 ms throttle/brake timing, physical braking,
  link-loss response and status timing remain unmeasured.
