# Lab 3 pinout

## Lab 3 Raspberry Pi LED additions

This is the user-selected **Lab 3 wiring plan**, not confirmation of completed
wiring or software support. These allocations match the cockpit LED rows already
committed in `lab4/Pin-map.csv` on branch `lab4` (commit `c92dc07`); they were
previously missing from this shared pinout document. They do not change the
existing CAN module connections or timing-marker pins.

| External LED / signal | Pi GPIO (BCM numbering) | Physical 40-pin header position |
|---|---|---|
| Bus A degraded / `DEG_A` | GPIO5 | **29** |
| Bus B degraded / `DEG_B` | GPIO6 | **31** |
| Red error-status LED / `ERR` | GPIO12 | **32** |
| LED ground return | GND | **39** |

**Board-facing orientation:** look at the Pi 4's component side with the USB and
Ethernet ports at the bottom. The GPIO header is on your right; pin 1 is its
top-left hole. Odd-numbered pins are the inner/left column and even-numbered pins
are the outer/right column. Physical pin 32 is beside pin 31; GPIO12 does **not**
mean physical pin 12.

Use one series resistor per LED, following the team's 470-ohm LED circuit:
`GPIO -> resistor -> LED anode (+)`, then `LED cathode (-) -> GND`.
These are active-high connections. `ERR` is an external red error LED, not the
Pi's onboard red power LED. Power off all supplies before changing wiring.

**Assignment evidence:** [Lab 3 handout](18-449_649%20Lab%203%20-%20Dual-CAN%20v1_0.pdf),
Part 5, pages 16–17, explicitly requires two per-bus degraded LEDs on every node,
including the Pi. Page 17's Pi test-point column omits `ERR`, but page 19's
checkoff requires “ERR high on all three.” The user chose to include the red
Pi `ERR` LED to cover that checkoff requirement; the handout does not explicitly
specify its color or GPIO number. The GPIO/header mapping and component-side
orientation were checked against the [official Raspberry Pi GPIO diagram](https://www.raspberrypi.com/documentation/computers/images/GPIO-Pinout-Diagram-2.png).

## Lab 3 handout erratum: CAN module MOSI/MISO are reversed

**The Lab 3 v1.0 handout's XIAO CAN expansion-board D9/D10 mapping is WRONG. The actual expansion board uses D9 = MISO and D10 = MOSI. Use the table below for all six modules, on both the Pi and Nucleos.** Earlier assistant instructions copied the handout's incorrect mapping; those instructions are superseded.

| XIAO CAN expansion-board pin | SPI signal | Raspberry Pi physical pin / BCM | NUCLEO-F401RE SPI1 pin / header |
|---|---|---|---|
| D8 | SCK | 23 / GPIO11 | PA5 / D13 |
| **D9** | **MISO** | **21 / GPIO9** | **PA6 / D12** |
| **D10** | **MOSI** | **19 / GPIO10** | **PA7 / D11** |

The module's D labels and the Nucleo's Arduino D labels are different pin-numbering systems. Connect MOSI to MOSI and MISO to MISO; SPI is not crossed like UART TX/RX. Keep the current working Pi wiring. The correction does not change the host SPI pinctrl assignments, 16 MHz oscillator configuration, 500 kbit/s target, CS/INT allocations, or 3.3 V supply requirement. Nucleo physical wiring still needs verification against this corrected table.

Sources checked after the user's correction:

- [Seeed XIAO CAN Bus Expansion Board documentation](https://wiki.seeedstudio.com/xiao-can-bus-expansion/) and its [manufacturer SCH/PCB archive](https://files.seeedstudio.com/wiki/xiao_can_bus_board/CAN_DEV_XIAO.zip). In `CAN_DEV_XIAO.sch`, MOSI connects J3 pin 4 to MCP2515 U3 SI; MISO connects J3 pin 5 to U3 SO. These are the XIAO D10 and D9 header positions respectively.
- [Seeed XIAO pin-multiplexing documentation](https://wiki.seeedstudio.com/xiao_pin_multiplexing_esp32c6/) identifies D10 as MOSI and D9 as MISO.
- Team bench evidence: the user restored this arrangement and both Pi CAN controllers started in normal mode at 500 kbit/s. This proves controller startup, not end-to-end CAN traffic. See [Lab 3 bring-up results](LAB3_CAN_BRINGUP.md).

### Lab 3 measurement-only GPIO allocation

The updated `lab3_wcet_baseline` overlay allocates **PC8** as `TASK_BODY`, a selectable elapsed-task pulse controlled by the serial command `timing probe NAME`. This pin is separate from the existing CAN SPI/CS/INT signals and other baseline test points. Both measurement images are flashed. PC8/CN10-2 was scope-verified on the board ending 124020, first as N3 and then as N2 after the firmware-role swap. The scope has since moved to Pi GPIO17/physical11 and GPIO27/physical13; see the bring-up record for current setup. Keep PC8 isolated from actuator inputs. At the user's request, the measurement overlay now uses the built-in blue B1 button on PC13, active-low, instead of the external PA8 test input. Both updated images passed boot checks, and B1 press processing was scope-verified. See [measurement definitions](../lab3_wcet_baseline/lab3_wcet_baseline/README_WCET_BASELINE.md).

## Lab 2 reference (historical)

The sections below retain the Lab 2 assignments; they are not the Lab 3 wiring
plan. In particular, the Lab 2 front-left/front-right pins must not be restored
on the Lab 3 Nucleos: PB6/D10 and PA5/D13 are used by CAN CS and SPI SCK there.

**Integration branch:** the root app now combines these motor, encoder, UART,
four-lamp and PB9 servo assignments. PA5 is only the front-right blinker, and
TIM2 stays enabled on PB10 for the right motor. TIM3 motor PWM and TIM4 servo
PWM are independent. No combined-board wiring or runtime test is claimed by
this merge; standalone branch descriptions below retain their historical scope.

Board: **NUCLEO-F401RE** (confirmed by the team).

**Part 3.5 update:** the root app now enables ADC1 on PA0/A0, PA1/A1 and PB0/A3,
channels 0/1/8, for left-motor/right-motor/servo currents. ADC clock is 21 MHz,
resolution 12 bits and reference nominally 3.3 V. The user chose direct ACS712
5A output connections with no divider and a 4.320 A upper-ADC-rail endpoint
magnitude: -4320 mA reversed motor sensors/+4320 mA servo. Sensor
power remains 5 V. This is implemented pin configuration, not confirmed wiring
or a physical test. See [current-sensing details](CURRENT_SENSOR_HANDOFF.md).
Older integration-status descriptions below predate this update.

**Part 4 additions (new allocation, not yet wired/tested):** CMD_RX is PC2,
Morpho CN7-35; PWM_SET is PC3, Morpho CN7-37. These do not replace any actuator
pin. Pi markers are BCM17/physical11 and BCM27/physical13. The complete 13-row
probe-board mapping and source references are in [PART4_TIMING](PART4_TIMING.md).
Tianyi subsequently reports 3.3 steering and 3.4 blinkers tested individually;
historical pending-test descriptions below do not negate that newer report.

Source: team-provided screenshot of **Lab 2 - Part 1 Wheel Input Results**, section **Tentative pin assignments for STM32** (rows 35–50).

These are tentative assignments transcribed from the screenshot, with the team's subsequent clarification: **the four rows labeled “motor DIR A/B” actually mean motor encoder A/B inputs, not L298N direction outputs.** The encoder assignments below reflect that clarification; the rest is not a verified as-built wiring record. The root `stm32_zephyr/app.overlay` now reuses the verified bench motor/encoder assignments and enables the Pi UART. That integrated image is built/host-tested but not flashed; servo, blinkers and ADC remain unintegrated. Connector and alternate-function mappings must be checked against the board documentation before use.

The [team Google Sheet](https://docs.google.com/spreadsheets/d/1dooWs_u2aW8KV9ROrJsESd9B8kbxStf5QkPFaePCx2k/edit?gid=177898744#gid=177898744) has now been updated to the recommended revision below: encoder names corrected in rows 39–42, steering moved to PB9/D14/TIM4_CH4 in row 43, and L298N IN1–IN4 assignments added in rows 51–54. Changes were verified saved to Drive. This records the wiring plan, not confirmation that the hardware has been rewired.

## Original team pin table (before the steering revision)

| Function | STM32 pin | Nucleo connector label | Peripheral |
|---|---|---|---|
| UART TX → Pi RX | PA9 | D8 | USART1_TX |
| UART RX ← Pi TX | PA10 | D2 | USART1_RX |
| Left motor PWM | PB4 | D5 | TIM3_CH1 |
| Right motor PWM | PB10 | D6 | TIM2_CH3 |
| Left encoder A (sheet: Left motor DIR A) | PB3 | D3 | GPIO input |
| Left encoder B (sheet: Left motor DIR B) | PA8 | D7 | GPIO input |
| Right encoder A (sheet: Right motor DIR A) | PB5 | D4 | GPIO input |
| Right encoder B (sheet: Right motor DIR B) | PA7 | D11 | GPIO input |
| Steering servo PWM | PC7 | D9 | TIM3_CH2 |
| Front-left blinker | PB6 | D10 | GPIO |
| Front-right blinker | PA5 | D13 | GPIO |
| Rear-left blinker | PA4 | A2 | GPIO |
| Rear-right blinker | PB8 | D15 | GPIO |
| Motor current #1 | PA0 | A0 | ADC1_IN0 |
| Motor current #2 | PA1 | A1 | ADC1_IN1 |
| Servo current | PB0 | A3 | ADC1_IN8 |

`D…` and `A…` are Arduino-style header labels, not physical header-position numbers.

## Encoder connections — confirmed by the team

### Separate Part 3.4 LED board — user-confirmed wiring

Tianyi is using another NUCLEO-F401RE while the teammate uses the motor board.
Rear-left yellow is A2/PA4; rear-right blue is D15/PB8; front-left red is
D10/PB6; front-right white is D13/PA5. Each has a 470-ohm resistor to GND,
with the LED anode toward the GPIO (active high). All four connections are
user-reported; actual light output and polarity await visual testing.
The wheel and Pi UART link are available. This does not establish that the
motor board has been rewired or shares this board's power arrangement.

On the blinker branch PA5 is no longer a link indicator; the onboard green LED
follows front-right. I2C1, SPI1 and board-default PA5 PWM are disabled to avoid
pin conflicts. See [Part 3.4 verification results](PART3_4_RESULTS.md).

Encoder VCC is connected to Nucleo **3V3** and encoder GND to Nucleo **GND**.

| Signal | STM32 pin / connector | EXTI line for GPIO interrupts |
|---|---|---|
| Left encoder A | PB3 / D3 | 3 |
| Left encoder B | PA8 / D7 | 8 |
| Right encoder A | PB5 / D4 | 5 |
| Right encoder B | PA7 / D11 | 7 |

These four signals use distinct EXTI line numbers, so there is no EXTI source-selection conflict between them. Some lines share an IRQ vector, which is not the same as a pin-source conflict. Hardware timer encoder mode instead requires compatible timer channel pins; this assignment is intended for GPIO decoding.

**Do not configure these pins as motor-control outputs or connect L298N IN1–IN4 to them while the encoders are attached.**

### Hand-turn verification

Both encoders passed separate 20-second USB-serial captures using the standalone
[`bringup/encoder_test`](../bringup/encoder_test/README.md) firmware. Each selected
wheel counted in both directions while the other count stayed fixed, with zero
invalid transitions and zero GPIO read errors. The user confirmed turning each
wheel vehicle-forward first:

| Wheel | Raw count change for vehicle-forward | Future velocity delta correction |
|---|---|---|
| Left | Negative | Negate raw delta |
| Right | Positive | Keep raw delta |

Apply these sign corrections **before averaging wheel velocities**, otherwise
forward travel can cancel out. Firmware currently prints raw counts. One marked
wheel revolution measured 1319 counts on the left and 1327 on the right, supporting
**1320 counts/wheel revolution as the provisional x4 calibration** (not 3960).
See [the calibration record](ENCODER_SPEC.md). The user reports a **75 mm** wheel
outside diameter, giving geometric circumference **235.6 mm**. A refined
multi-revolution count calibration and loaded rolling circumference remain
unmeasured.

## Recommended revision — proposed, not yet confirmed wired

On `lab2-tianyi-steering`, the separate bench firmware now configures
**D14/PB9/TIM4_CH4** at 20 ms, initially zero pulse width. Physical servo wiring
and endpoint calibration are still unconfirmed. PB8/D15 remains the blue LED.
TIM4 uses prescaler 83 from the board's 84 MHz timer clock (1 us ticks).
This does not reassign the motor teammate's pins or modify that board.

**Move only the steering PWM assignment from PC7/D9 (`TIM3_CH2`) to PB9/D14 (`TIM4_CH4`, AF2).** Keep both motor PWM assignments and all encoder connections unchanged. PB9/D14 was unused in the original table.

| PWM function | STM32 pin | Header label | Timer channel |
|---|---|---|---|
| Left motor / ENA | PB4 | D5 | TIM3_CH1 |
| Right motor / ENB | PB10 | D6 | TIM2_CH3 |
| Steering servo signal | **PB9** | **D14** | **TIM4_CH4** |

Each PWM now has its own timer period. Start with a servo period supported by the actual servo (commonly 20 ms / 50 Hz); choose motor PWM frequency independently after checking the driver and motor behavior. Moving the servo signal does not change its power supply requirements.

## L298N controls — user-confirmed wired; first powered movement observed

The user subsequently reported **all six motor-control wires connected** according to the table below and confirmed **ENA/ENB jumper caps removed**. This supersedes the earlier IN1–IN4-disconnected report. Physical wiring has not been independently inspected. These assignments use the newly freed D9 and three other Arduino-style pins without reusing encoder pins.

Assuming the left motor is on OUT1/OUT2 and the right motor is on OUT3/OUT4:

| L298N input | Team signal | STM32 pin | Header label |
|---|---|---|---|
| ENA | Left motor PWM | PB4 | D5 |
| IN1 | Left bridge input 1 | PC7 | D9 |
| IN2 | Left bridge input 2 | PA6 | D12 |
| IN3 | Right bridge input 1 | PC1 | A4 |
| IN4 | Right bridge input 2 | PC0 | A5 |
| ENB | Right motor PWM | PB10 | D6 |

A4 and A5 are usable as digital GPIO outputs; their header names do not restrict them to analog use. This assumes the board's standard solder-bridge routing. Configure PC7 and PA6 as ordinary GPIO here, not as timer channels. Keep USART2 on PA2/D1 and PA3/D0 available for the ST-LINK serial console.

Do not apply motor power with IN1–IN4 floating. Before powered tests, establish defined inactive control levels during boot/reset as well as after firmware initialization.

The user confirmed **ENA and ENB jumpers removed** before the motor-test flash. Keep those jumpers removed while MCU PWM wires are connected. They would otherwise hold the channels enabled and are separate from the module's 5 V regulator jumper. The user subsequently confirmed the separate 5V-EN regulator jumper is installed and measured the driver's +5V terminal relative to GND at **5 V** with a multimeter.

The standalone [`bringup/motor_test`](../bringup/motor_test/README.md) firmware has been compiled/flashed and reports zero duty with all six MCU control-pin inputs reading low. Separate 20%-duty, nominal 500 ms left/right commands subsequently returned to disabled without firmware faults, but the user reports **neither wheel moved and a beep was heard**. A subsequent 35% trial also produced only a beep and no wheel movement. A left-only 50% trial also failed to start the wheel. Subsequently, the user confirmed wheel movement from a single LEFT-command **100% / nominal 200 ms** kick. Subsequent encoder-observed 100% / 200 ms kicks verified the channel identities: **IN1=1/IN2=0 moves the left wheel backward** (raw left count increases; also visually confirmed), and **IN3=1/IN4=0 moves the right wheel forward** (raw right count increases). The other encoder remained unchanged in each test, with no reported invalid transitions or GPIO errors. Left-forward therefore uses **IN1=0/IN2=1**, and right-forward uses **IN3=1/IN4=0**. Both forward settings were subsequently verified together in one user-requested 100% / nominal 5-second trial: left counts decreased, right counts increased, with no reported invalid transitions, GPIO errors or firmware faults. Outputs automatically returned to IN=0000/EN=00; wheels coasted afterward. Current diagnostic firmware includes a per-wheel no-progress/reversal guard, not current limiting. A post-trial console/control-priority correction was flashed and checked idle only. PWM waveform, exact physical stop timing, long-term/ground-loaded operation and current limits remain unverified. The root Pi-link application now reuses these motor/encoder pins and the bench PID, with hardware validation still pending.

The 2026-09-27 startup sweep kept these pins and forward polarities unchanged.
At 10 kHz, separate 200 ms forward starts failed at 50% on each motor, passed
3/3 at 55% on each, and passed 1/1 at 60% on each. The user subsequently required
both motors together. The simultaneous batch confirmed 55% startup 3/3 and 40%
four-second holding 3/3 after a 60% kick; 50% startup and 35% holding failed.
Current flashed limits are 60% / 200 ms startup, or a separate 60% / 200 ms kick
then 55% / maximum 4000 ms hold, with the same per-wheel motion guard. This
supersedes the five-second profile above. No pins or wiring changed; see the
[measurement record](MOTOR_CHARACTERIZATION.md). The current bench image also
supports average-speed PID; the first bounded 45 RPM BOTH-wheel test passed its
provisional tolerance. No pins or wiring changed for that test; details and
limits are in the same measurement record.

Use a common ground between the Nucleo, encoders, and motor driver. The team confirmed changing to **converter-fed E5V, JP5 on E5V, JP1 open**, with USB for flashing/debugging connected after external power is on. For initial software/encoder bring-up, disconnect the L298N's 12 V motor-power feed separately while keeping the converter branch available to power the Nucleo. Disconnect supplies before changing wiring. See [the team BOM and power setup](HARDWARE.md#current-power-setup) for details and verification limits.

## Issues to resolve before firmware integration

1. **Shared PWM timer:** left motor PB4 (`TIM3_CH1`) and steering PC7 (`TIM3_CH2`) share TIM3's period, though their pulse widths can differ. Using both at 50 Hz is technically possible if the servo supports that rate; the removed full-control starter used a 20 ms motor period. The integrated link app now uses the bench's separate 10 kHz motor timers. However, 50 Hz motor PWM gives long on/off intervals and may cause torque ripple or audible operation. Timer compare preloading can also delay a duty update until a period boundary, up to nearly 20 ms, which is unsuitable for guaranteeing the handout's 2 ms throttle response. Prefer a separate timer for the servo and a higher motor PWM frequency, selected against driver limits and measured behavior. The servo's actual supported period still needs confirmation.
2. **Blinky shares PA5:** on this board, the onboard user LED uses PA5/D13, also assigned above to the front-right blinker. Check what is physically connected there before flashing the stock blinky sample or the current link app, which also drives that LED.
3. **Motor direction integration:** the sheet's four former “DIR” rows are encoder inputs, not driver outputs. The integrated app now uses all four IN1–IN4 GPIOs above, with left-forward 01 and right-forward 10. Its hardware validation is pending; it does not restore the removed starter's insufficient two-GPIO interface.
4. **Dynamic braking:** the integrated driver now sets both direction inputs low and holds each enable high, per ST L298 DS0218 Rev 5 Table 5. Enable-low is coast, used for released throttle and B1. The new braking code has not been flashed or physically tested.
5. **Missing test-point assignments:** additional software timing test points (`CMD_RX`, `PWM_SET`) are not present in this screenshot. Allocate them without conflicts before integration.

6. **Board-default peripheral conflicts:** the Zephyr v4.3.0 board DTS assigns USART1 to PB6/PB7, enables I2C1 on PB8/PB9 and I2C3 on PA8/PC9, describes SPI1 on PA5/PA6/PA7 with PB6 chip select, and maps TIM2 PWM to PA5. The link app's overlay already remaps USART1 to PA9/PA10. Actuator integration must also remap TIM2 PWM to PB10 and disable unused conflicting peripherals/pin configurations. Do not assume selecting aliases alone frees those pins.

## Mapping references

Checked against Zephyr's board and STM32 pinctrl definitions:

- [NUCLEO-F401RE Arduino header mapping (Zephyr v4.3.0)](https://github.com/zephyrproject-rtos/zephyr/blob/v4.3.0/boards/st/nucleo_f401re/arduino_r3_connector.dtsi)
- [NUCLEO-F401RE board defaults (Zephyr v4.3.0)](https://github.com/zephyrproject-rtos/zephyr/blob/v4.3.0/boards/st/nucleo_f401re/nucleo_f401re.dts)
- [STM32F401R pinctrl definitions (hal_stm32 main)](https://github.com/zephyrproject-rtos/hal_stm32/blob/main/dts/st/f4/stm32f401r(d-e)tx-pinctrl.dtsi): `tim4_ch4_pb9` uses AF2.

See also: [Lab 2 handout](18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf).

## Local motor stop button

The motor bench configures the Nucleo B1 USER button through board alias `sw0`,
PC13 active-low, with a pull-up, edge interrupt and control-thread polling. EXTI13
does not conflict with the four encoder EXTI inputs. A press latches both motor
outputs off until reset. The initial flashed idle check reported B1 released; a
physical press-to-stop result must be recorded separately from this pin mapping.
