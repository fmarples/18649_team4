# STM32 pin assignments — Lab 2

Board: **NUCLEO-F401RE** (confirmed by the team).

Source: team-provided screenshot of **Lab 2 - Part 1 Wheel Input Results**, section **Tentative pin assignments for STM32** (rows 35–50).

These are tentative assignments transcribed from the screenshot, with the team's subsequent clarification: **the four rows labeled “motor DIR A/B” actually mean motor encoder A/B inputs, not L298N direction outputs.** The encoder assignments below reflect that clarification; the rest is not a verified as-built wiring record. The starter's `stm32_zephyr/app.overlay` does not yet implement these assignments. Connector and alternate-function mappings must be checked against the board documentation before use.

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

## Recommended revision — proposed, not yet confirmed wired

**Move only the steering PWM assignment from PC7/D9 (`TIM3_CH2`) to PB9/D14 (`TIM4_CH4`, AF2).** Keep both motor PWM assignments and all encoder connections unchanged. PB9/D14 was unused in the original table.

| PWM function | STM32 pin | Header label | Timer channel |
|---|---|---|---|
| Left motor / ENA | PB4 | D5 | TIM3_CH1 |
| Right motor / ENB | PB10 | D6 | TIM2_CH3 |
| Steering servo signal | **PB9** | **D14** | **TIM4_CH4** |

Each PWM now has its own timer period. Start with a servo period supported by the actual servo (commonly 20 ms / 50 Hz); choose motor PWM frequency independently after checking the driver and motor behavior. Moving the servo signal does not change its power supply requirements.

## L298N direction inputs — currently disconnected; proposed assignment

The team confirmed **IN1–IN4 are not connected to anything**. The following proposal uses the newly freed D9 and three other unused Arduino-style pins; it does not reuse encoder pins.

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

The team reported ENA and ENB jumpers are currently installed. **Remove those jumpers with power off before connecting MCU PWM outputs.** They hold the channels enabled and are separate from the module's 5 V regulator jumper. Verify which header pin is the enable signal rather than the jumper's supply side.

Use a common ground between the Nucleo, encoders, and motor driver. The team confirmed changing to **converter-fed E5V, JP5 on E5V, JP1 open**, with USB for flashing/debugging connected after external power is on. For initial software/encoder bring-up, disconnect the L298N's 12 V motor-power feed separately while keeping the converter branch available to power the Nucleo. Disconnect supplies before changing wiring. See [the team BOM and power setup](HARDWARE.md#current-power-setup) for details and verification limits.

## Issues to resolve before firmware integration

1. **Shared PWM timer:** left motor PB4 (`TIM3_CH1`) and steering PC7 (`TIM3_CH2`) share TIM3's period, though their pulse widths can differ. Using both at 50 Hz is technically possible if the servo supports that rate; the starter currently sets the motor period to 20 ms too. However, 50 Hz motor PWM gives long on/off intervals and may cause torque ripple or audible operation. Timer compare preloading can also delay a duty update until a period boundary, up to nearly 20 ms, which is unsuitable for guaranteeing the handout's 2 ms throttle response. Prefer a separate timer for the servo and a higher motor PWM frequency, selected against driver limits and measured behavior. The servo's actual supported period still needs confirmation.
2. **Blinky shares PA5:** on this board, the onboard user LED uses PA5/D13, also assigned above to the front-right blinker. Check what is physically connected there before flashing the stock blinky sample.
3. **Motor direction implementation missing:** the sheet's four “DIR” rows are encoder inputs, not driver outputs. The proposed IN1–IN4 assignment above supplies four independent GPIOs, but the starter `motor.c` exposes only two direction GPIOs. Update the driver and devicetree before using this proposal.
4. **Dynamic braking:** the starter sets enable PWM to zero before setting direction inputs equal. L298N enable-low is coast, not dynamic braking. For dynamic braking, the channel must be enabled with its two direction inputs equal; verify the module truth table before powered tests.
5. **Missing test-point assignments:** additional software timing test points (`CMD_RX`, `PWM_SET`) are not present in this screenshot. Allocate them without conflicts before integration.

6. **Board-default peripheral conflicts:** the Zephyr v4.3.0 board DTS assigns USART1 to PB6/PB7, enables I2C1 on PB8/PB9 and I2C3 on PA8/PC9, describes SPI1 on PA5/PA6/PA7 with PB6 chip select, and maps TIM2 PWM to PA5. The application overlay must remap USART1 to PA9/PA10, remap TIM2 PWM to PB10, and disable unused conflicting peripherals/pin configurations. Do not assume selecting aliases alone frees those pins.

## Mapping references

Checked against Zephyr's board and STM32 pinctrl definitions:

- [NUCLEO-F401RE Arduino header mapping (Zephyr v4.3.0)](https://github.com/zephyrproject-rtos/zephyr/blob/v4.3.0/boards/st/nucleo_f401re/arduino_r3_connector.dtsi)
- [NUCLEO-F401RE board defaults (Zephyr v4.3.0)](https://github.com/zephyrproject-rtos/zephyr/blob/v4.3.0/boards/st/nucleo_f401re/nucleo_f401re.dts)
- [STM32F401R pinctrl definitions (hal_stm32 main)](https://github.com/zephyrproject-rtos/hal_stm32/blob/main/dts/st/f4/stm32f401r(d-e)tx-pinctrl.dtsi): `tim4_ch4_pb9` uses AF2.

See also: [Lab 2 handout](18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf).
