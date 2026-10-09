# Pi-to-STM32 integrated actuator link

The root application combines main's encoder/PID motor driver with Tianyi's
blinkers, wheel-button self-test and Pi-controlled steering on one NUCLEO-F401RE.
Part 3.5 now samples three ACS712 5A sensors through ADC1 with nominal
calibration and a user-selected 4.320 A upper-ADC-rail endpoint magnitude. Physical current
verification and physical testing of console-independent steering remain pending.
See `doc/INTEGRATION.md` for verification and deployment limits.

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
Button bit n represents Part 1's zero-based raw index n. Paddle 5 selects left
and paddle 4 selects right. A/button 0 controls the **Pi-local** self-test hazard;
the bridge consumes it and clears bit 0 in every transmitted command. Pedals
are 32767 released and -32768 fully pressed. Frame layout and CRC are unchanged.

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
- Brake pedal, startup without a link, invalid command, link timeout, manual
  self-test or a latched servo/blinker peripheral failure with a healthy driver:
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

## Blinkers, self-test and steering

PA5/D13 is exclusively the front-right blinker (onboard LD2 follows it), not
a link indicator. Other lamps are FL PB6/D10, RL PA4/A2 and RR PB8/D15.
Normal blink is 1 Hz at 50%; hazards are 2 Hz. Left/right paddle presses are
edge-triggered and mutually exclusive. Crossing +/-8000 raw steering and
returning inside +/-6000 cancels the selected side; steering does not select it.

A/button 0 latches the Pi's self-test hazard on its first accepted press;
a second press within 400 ms clears it, with a minimum 20 ms release between
presses. Holding A or releasing it alone does not clear the latch. If the first
press is older than 400 ms, a fresh double press is needed. Only validated,
advancing wheel UDP packets from the permitted sender affect the latch.
Intervals use Pi acceptance time at millisecond precision, not a wheel-side
timestamp. Queued packets can compress a release interval, leaving the hazard
latched until the user retries a double press.

While latched, the Pi sends **no UART commands**, including periodic refreshes
and stale/invalid-input brake frames. It keeps consuming wheel input and reading,
logging and forwarding STM32 status. The existing STM32 watchdog detects command
silence at 60 ms, reports ERROR_TIMEOUT (2), dynamically brakes healthy motors,
flashes hazards and disables LIVE steering. The Pi latch survives UDP loss,
invalid packets and UDP counter restarts; none of those events clear it.

Clearing the Pi latch resumes current valid pedals (including nonzero throttle)
and non-A buttons immediately. It never clears motor/B1/peripheral faults;
steering still waits for the Logitech wheel to return near center. Firmware's
existing direct-command SELF_TEST (6) handler and the wire state codes remain
unchanged, but normal A-button self-test now uses the timeout path, not state 6.
See [issue #2](https://github.com/fmarples/18649_team4/issues/2).

Servo is PB9/D14 on TIM4, 20 ms period. Motor PWM remains PB4/TIM3 and PB10/TIM2
at 10 kHz. USB USART2 accepts the existing ASCII calibration commands; binary
Pi USART1 is unchanged. At boot the firmware loads the tracked calibration and
enters WAIT_CENTER with PWM disabled. A healthy Pi link, no inhibiting fault and
raw steering within inclusive -2000..2000 enable LIVE. No USB cable, ARM command
or USB heartbeat is required for vehicle steering. LIVE follows the Pi steering
value, including while blinkers operate. Link loss, self-test or invalid steering
disables PWM and returns to WAIT_CENTER; recovery must satisfy the same centered
wheel interlock. Motor and peripheral faults continue to inhibit output; latched
faults still require their existing reset procedure.

USB remains optional for manual calibration/diagnostics. Manual mode retains its
500 ms USB heartbeat and can run without Pi traffic. Explicit OFF stays OFF;
SERVO AUTO returns to WAIT_CENTER. ARM/LIVE still support manual calibration.
Opening the calibration console sends OFF; its normal quit also sends OFF.
A physical USB disconnect alone does not stop LIVE, which is governed by the Pi link.

`config/servo_calibration.json` holds user-selected left/center/right
1200/1600/2000 us. CMake embeds this file in firmware; updating the vehicle's
boot calibration requires rebuilding/flashing. The Windows helper prefers locally saved calibration, falling
back to this tracked file only when the default local file is missing. An
explicit --file path never silently falls back. Loading changes no output;
these numbers are not proof of measured mechanical limits.

Status 5 remains ERROR_MOTOR from main. SELF_TEST is now **6**, unlike the old
steering-only bench's 5, and ERROR_ACTUATOR is **7**. Update the Pi decoder
alongside this firmware. Motor faults have reporting priority over peripheral
faults, then transport errors, then manual self-test. Motor/B1 faults retain
main's latched enable-low/coast behavior; a healthy motor driver dynamically
brakes for self-test or an actuator peripheral failure. A failed output driver
cannot guarantee physical braking or lamp output.

## Status: 56 bytes, STM32 to Pi

| Byte offset | Size | Meaning |
| --- | --- | --- |
| 0, 2, 3 | 2, 1, 1 | L2, version 1, type 2 |
| 4 | 4 | Unsigned status sequence |
| 8 | 4 | STM32 uptime in milliseconds, wraps modulo 2^32 |
| 12 | 4 | Last accepted command sequence |
| 16 | 4 | State: 0 WAITING, 1 LINK_OK, 2 timeout, 3 bad input, 4 overflow, 5 motor fault, 6 self-test, 7 actuator fault |
| 20, 24, 28 | 4 each | Current accepted/safe steering, throttle, brake values |
| 32, 36, 40 | 4 each | Signed left-motor, right-motor, servo current in mA |
| 44 | 4 | Current validity mask: bits 0, 1, 2 correspond to these sensors |
| 48 | 4 | Rejected-frame/overflow counter |
| 52 | 4 | CRC-32/IEEE of bytes 0 through 51 |

A dedicated priority-3 workqueue samples ADC1 channels 0/1/8 every 20 ms,
corresponding to left/right/servo on PA0/PA1/PB0. Each acquisition averages eight
scans, converts with per-channel constants and publishes a short mutex-protected
snapshot. Defaults are vendor nominal: 2.5 V zero, 185 mV/A and 3.3 V reference,
not measured bench calibration. Status never waits for ADC conversion.

The user chose direct ADC wiring with no divider and confirmed reversed
orientation for both motor sensors. Motors convert `(zero - output)` voltage;
servo converts `(output - zero)`. A channel reaching the ADC's maximum code,
or exceeding its upper-voltage reporting endpoint, reports **-4320 mA for motors
or +4320 mA for servo, with its validity bit set**. `[CEILING]` denotes the ADC
voltage ceiling, not exact current. Falling-voltage readings remain measurable
beyond 4.320 A in magnitude; there is no symmetric current cap. Pi console and
Windows views recognize the per-channel signed endpoint. CSV and wire values
remain numeric. There is no added flag or frame-layout change.

Setup/read errors clear all current validity immediately on publication. Validity
also expires at 100 ms sample age, measured from before acquisition. Invalid
fields are INT32_MIN, NOT measured 0 mA. A successful ADC conversion does not
detect a floating/disconnected sensor or certify calibration. See
`doc/CURRENT_SENSOR_HANDOFF.md` for conversion, filtering, logs and pending tests.
The state enum describes transport, self-test and latched motor/actuator faults;
current errors never change actuator policy in this read-only lab. Steering
status is commanded input, not an angle measurement.

## Read-only laptop telemetry

The Pi bridge forwards each validated 56-byte status as one UDP datagram to
laptop port **8002**. It learns the destination IP from an accepted advancing
wheel packet, or uses `--telemetry-host`. Forwarding continues after wheel input
stops so the GUI can show timeout/error status. This path never targets the
course proxy's force-feedback port 8001; ports 8000/8001 are rejected as telemetry
port overrides. UART framing, CRC and the command path are unchanged.

The laptop launcher provides separate Raw log and Current chart windows, checks
the Pi source IP and frame CRC, and rejects duplicates/reordering while linked.
After 500 ms without accepted data, it shows stale readings and permits a new
sequence baseline for a reboot/reconnect. An identical sequence/uptime duplicate
never refreshes the display. The 500 ms value is a GUI freshness rule only, not
a vehicle timeout. UDP send errors do not stop the Pi's command processing.
See [GUI telemetry](doc/GUI_TELEMETRY.md) for deployment and log/crash paths.

## Timing and failure behavior

- Outside the Pi-local A hazard, Pi forwards each newly received, valid,
  advancing wheel UDP packet with A's bit removed.
- Between UDP updates, Pi refreshes the latest state about every 20 ms unless
  the A hazard is latched. Latching suppresses all command writes immediately;
  bytes already buffered or on the UART wire cannot be recalled.
- Outside the A hazard, after 80 ms without fresh valid UDP, Pi sends one released-throttle/full-brake
  frame, then pauses commands. It drains queued UDP before recovery so an expired
  backlog cannot immediately undo the stop. Duplicate/backward counters do not
  refresh input. A new sequence baseline is allowed only after input timeout.
  Invalid UDP also sends a brake frame and pauses; it preserves the previous
  valid counter/time until a real timeout.
- STM32 checks for command timeout each owner iteration (1 ms wait when idle)
  and enters its link error state at 60 ms since the last accepted frame's
  reception time: three missed 20 ms updates, as required by the handout.
- A periodic Zephyr timer requests status every 20 ms. Actual wire timing
  must be measured; successful compilation does not prove the +/-10% limit.
- The handout says 150 ms in Part 2 and 100 ms in final checkoff; 60 ms also
  targets the explicit three-missed-update requirement. It is an implementation
  threshold, not a measured physical stopping time. For issue #2, the user
  confirmed retaining this timeout and the existing single/double-press controls.
  Timeout-based A self-test targets checkoff's 100 ms limit, not the conflicting
  requirements-table 10 ms limit. Physical timing still needs measurement.
- The explicit upstream brake avoids waiting for both freshness and MCU timeout
  before braking. Upstream UDP freshness is 80 ms; cable timeout is 60 ms,
  but Python/OS scheduling, UART transmission and output latency still need
  measurement. A crashed Pi bridge is handled by the MCU's 60 ms timeout.
  A UDP-stale brake frame still looks like a healthy-link brake command, so
  hazards follow after a further MCU timeout. No <=100 ms UDP-loss-to-hazards
  claim is made; UART cable loss and upstream UDP loss are different cases.
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
  The main owner applies motor policy, hazards and steering interlocks above.
  Fresh valid commands recover ordinary link errors, but never clear B1 or a
  latched motor fault.

## Thread responsibilities

| Context | Responsibility |
| --- | --- |
| UART ISR | Collect candidate frames; timestamp completion; enqueue |
| Main, priority 1 | Validate commands; timeout; self-test; encoders/B1/PID; own motor, lamp and servo writes |
| Status, priority 2 | Transmit one binary status after each 20 ms timer event |
| Dedicated current workqueue, priority 3 | Delayed work samples backend and publishes current validity; no actuator policy |
| Console, priority 4 | Print queued servo replies; human-readable diagnostics approximately every 250 ms |

Lower Zephyr priority numbers here have higher scheduling priority. Console
prints are throttled so debugging does not define the link's heartbeat rate.
The console's 250 ms print interval is not a link-loss timing measurement.
Normal servo replies are queued nonblocking by the main owner and printed in
the diagnostic thread, so command replies do not stall motor updates or
interleave with periodic diagnostics. That thread checks for replies every
10 ms between diagnostic bursts; host request timeouts still apply.

## Files and validation

For current Part 4 build/test evidence use `doc/PART4_SOFTWARE_RESULTS.md`.
Build output is `build/part4`; deploy all `pi/*.py` files together because the
bridge now imports `timing_gpio.py` even when markers are off. The remaining
paths below describe the previous main-branch motor integration.

- stm32_zephyr/: root application; the integration was built in `build/pi-motor/`.
- pi/part2_bridge.py and pi/part2_protocol.py: copy both into ~/18649/part2.
- test_protocol.py: host tests for layout, CRC, raw axes/button extraction,
  stream resynchronization, sequence wrap, and stopping stale UDP refreshes.
- Issue #2 software checks: `tests/test_bridge_freshness.py` exercises A latching,
  double-press/debounce boundaries, silence through invalid/stale input, counter
  restart, duplicate rejection, non-A buttons and continued status forwarding.
  Persistent local logs (Git-ignored): `logs/issue-2/bridge-green.log`, `tests.log`, `protocol.log`
  and `compile.log`; failing-before-fix evidence: `red.log` and `recovery-red.log`.
  Verification: 80 host tests (including native GCC controller builds), 10
  protocol tests and Python byte compilation passed, with no skipped host tests.
  The STM32 source/image is unchanged; no Zephyr rebuild was performed because
  the documented Zephyr workspace/SDK were not found on this machine. No Pi deployment, flash
  or hardware test was requested for this fix.
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
