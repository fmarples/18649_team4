# STM32 pin assignments — Lab 2

Board: **NUCLEO-F401RE** (confirmed by the team).

Source: team-provided screenshot of **Lab 2 - Part 1 Wheel Input Results**, section **Tentative pin assignments for STM32** (rows 35–50).

These are tentative assignments transcribed from the screenshot, with the team's subsequent clarification: **the four rows labeled “motor DIR A/B” actually mean motor encoder A/B inputs, not L298N direction outputs.** The encoder assignments below reflect that clarification; the rest is not a verified as-built wiring record. The current link-only `stm32_zephyr/app.overlay` implements the UART assignment only; the remaining assignments are not integrated. Connector and alternate-function mappings must be checked against the board documentation before use.

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

The standalone [`bringup/motor_test`](../bringup/motor_test/README.md) firmware has been compiled/flashed and reports zero duty with all six MCU control-pin inputs reading low. Separate 20%-duty, nominal 500 ms left/right commands subsequently returned to disabled without firmware faults, but the user reports **neither wheel moved and a beep was heard**. A subsequent 35% trial also produced only a beep and no wheel movement. A left-only 50% trial also failed to start the wheel. Subsequently, the user confirmed wheel movement from a single LEFT-command **100% / nominal 200 ms** kick. Subsequent encoder-observed 100% / 200 ms kicks verified the channel identities: **IN1=1/IN2=0 moves the left wheel backward** (raw left count increases; also visually confirmed), and **IN3=1/IN4=0 moves the right wheel forward** (raw right count increases). The other encoder remained unchanged in each test, with no reported invalid transitions or GPIO errors. Left-forward therefore uses **IN1=0/IN2=1**, and right-forward uses **IN3=1/IN4=0**. Both forward settings were subsequently verified together in one user-requested 100% / nominal 5-second trial: left counts decreased, right counts increased, with no reported invalid transitions, GPIO errors or firmware faults. Outputs automatically returned to IN=0000/EN=00; wheels coasted afterward. Current diagnostic firmware includes a per-wheel no-progress/reversal guard, not current limiting. A post-trial console/control-priority correction was flashed and checked idle only. PWM waveform, exact physical stop timing, long-term/ground-loaded operation and current limits remain unverified. The Part 2 link application is unchanged and does not include this motor implementation.

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

1. **Shared PWM timer:** left motor PB4 (`TIM3_CH1`) and steering PC7 (`TIM3_CH2`) share TIM3's period, though their pulse widths can differ. Using both at 50 Hz is technically possible if the servo supports that rate; the removed full-control starter used a 20 ms motor period. The current link app has no motor PWM configuration. However, 50 Hz motor PWM gives long on/off intervals and may cause torque ripple or audible operation. Timer compare preloading can also delay a duty update until a period boundary, up to nearly 20 ms, which is unsuitable for guaranteeing the handout's 2 ms throttle response. Prefer a separate timer for the servo and a higher motor PWM frequency, selected against driver limits and measured behavior. The servo's actual supported period still needs confirmation.
2. **Blinky shares PA5:** on this board, the onboard user LED uses PA5/D13, also assigned above to the front-right blinker. Check what is physically connected there before flashing the stock blinky sample or the current link app, which also drives that LED.
3. **Motor direction implementation missing:** the sheet's four “DIR” rows are encoder inputs, not driver outputs. The proposed IN1–IN4 assignment above requires four independent GPIOs. The current link app has no motor driver; implement the driver and devicetree before using this proposal. The removed full-control starter's two-direction-GPIO interface was insufficient.
4. **Dynamic braking:** the removed full-control starter set enable PWM to zero before setting direction inputs equal; the current link app does not brake a motor. L298N enable-low is coast, not dynamic braking. For dynamic braking, the channel must be enabled with its two direction inputs equal; verify the module truth table before powered tests.
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
