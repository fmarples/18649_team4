# Part 2 UART link starter

**Part 3.3 steering branch:** binary layouts remain unchanged. The separate
bench adds opt-in servo PWM and the Part 3.4 state 5 below. USB/USART2 now has
an interrupt-buffered ASCII calibration console; it is separate from the
binary Pi UART. `SERVO KEEPALIVE` refreshes a 500 ms bench lease; losing that
lease disables PWM. The motor controller is still absent. Status axes remain
command readbacks, not measured servo positions. See `doc/PART3_3_START_HERE.md`.

**Part 3.4 branch note:** `lab2-tianyi-blinkers` keeps frame layouts and existing
state values unchanged, and adds status state **5 = SELF_TEST**. The STM32 drives four blinker LEDs:
button 5 selects left, button 4 selects right; raw steering controls self-cancel;
link errors and startup select hazards. A/button 0 single-press latches manual
self-test hazards; a double press within 400 ms clears only that latch. Link
faults still win. PA5 is front-right, no longer the link-status LED.
No motor/servo driver is present. The link-only physical-output statements
below describe the historical baseline. See `doc/PART3_4_START_HERE.md` for
current behavior and the future vehicle-error integration contract.

This is a team starter, not course-provided code or a complete vehicle controller.
It is for the kit Raspberry Pi 4 and NUCLEO-F401RE. Do not attach actuators yet.

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

## Status: 56 bytes, STM32 to Pi

| Byte offset | Size | Meaning |
| --- | --- | --- |
| 0, 2, 3 | 2, 1, 1 | L2, version 1, type 2 |
| 4 | 4 | Unsigned status sequence |
| 8 | 4 | STM32 uptime in milliseconds, wraps modulo 2^32 |
| 12 | 4 | Last accepted command sequence |
| 16 | 4 | State: 0 WAITING/startup fault, 1 LINK_OK/normal, 2 timeout, 3 bad input, 4 overflow, 5 manual SELF_TEST with healthy link |
| 20, 24, 28 | 4 each | Current accepted/safe steering, throttle, brake values |
| 32, 36, 40 | 4 each | Signed left-motor, right-motor, servo current in mA |
| 44 | 4 | Current validity mask: bits 0, 1, 2 correspond to these sensors |
| 48 | 4 | Rejected-frame/overflow counter |
| 52 | 4 | CRC-32/IEEE of bytes 0 through 51 |

Current values are INT32_MIN and validity is zero in this starter, because no
sensors are wired. These are unavailable readings, NOT measured 0 mA. Replace
them with calibrated readings after the sensors are connected. The state enum
currently describes the link; integrate the vehicle zone state later.

## Timing and failure behavior

- Pi forwards each newly received, valid, advancing wheel UDP packet.
- Between UDP updates, Pi refreshes the latest state about every 20 ms.
- After 100 ms without a fresh valid UDP packet, Pi stops commands. It never
  refreshes an old wheel state indefinitely. Duplicate/backward UDP counters
  do not make data fresh; a new baseline is allowed after an input timeout.
- STM32 checks for command timeout every roughly 1 ms and enters its link
  error state at 80 ms since the last accepted frame's reception time.
- A periodic Zephyr timer requests status every 20 ms. Actual wire timing
  must be measured; successful compilation does not prove the +/-10% limit.
- The handout says 150 ms in Part 2 and 100 ms in final checkoff. The 80 ms
  timeout targets the stricter checkoff with margin; confirm the conflict
  with the TA. This is a proposed implementation setting, not a measured result.
- A stopped UDP producer can take about 100 + 80 ms to cause a link error.
  This differs from unplugging the Pi-to-STM32 cable, which stops reception
  immediately. Revisit the whole-chain freshness budget before actuation.
- Bad CRC/range/button masks cannot update control values or refresh the
  timeout. Invalid complete candidates set ERROR_BAD_INPUT. Header noise or
  incomplete frames are ignored and eventually time out. A valid later frame
  restores LINK_OK. A corrupt/truncated candidate can consume part of the next
  frame; the parser recovers at a subsequent complete L2/version/type header.
- UART ISR gathers candidates into an eight-frame queue. On overflow it
  discards the backlog and sets a fault instead of applying old queued inputs.
  Already queued packets older than the timeout are rejected. This is a simple
  demonstration policy to review before the system has actuators.
- Duplicate/old UART sequence numbers while LINK_OK do not refresh the timer.
  After error/timeout, a valid frame establishes a new sequence baseline.
- Safe internal values are steering 0, throttle 32767, brake -32768. Only the
  onboard LED indicates link state. No motor braking, hazards, or servo action
  occurs until those drivers/state machines are implemented.

## Thread responsibilities

| Context | Responsibility |
| --- | --- |
| UART ISR | Collect candidate frames; timestamp completion; enqueue |
| Main, priority 1 | Validate CRC/ranges/sequence; enforce timeout; update LED |
| Status, priority 2 | Transmit one binary status after each 20 ms timer event |
| Console, priority 3 | Human-readable USB prints approximately every 250 ms |

Lower Zephyr priority numbers here have higher scheduling priority. Console
prints are throttled so debugging does not define the link's heartbeat rate.
The console's 250 ms print interval is not a link-loss timing measurement.

## Files and validation

- stm32_zephyr/: root-level Zephyr application, built in `build/part2/`.
- pi/part2_bridge.py and pi/part2_protocol.py: copy both into ~/18649/part2.
- test_protocol.py: host tests for layout, CRC, raw axes/button extraction,
  stream resynchronization, sequence wrap, and stopping stale UDP refreshes.
- Hardware operation, GPIO wiring, actual status timing and timeout timing
  require the team's bench tests. This starter does not complete all Lab 2.
