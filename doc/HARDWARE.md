# Team hardware BOM and power setup

This is a working BOM, not a completed purchasing list or an as-built schematic. The [Lab 2 handout](18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf), especially "What is in the kit" and Parts 3 and 5, supplies the baseline. Team confirmations refine it below. Quantities marked "target" come from the assignment, not a physical inventory.

## Team-confirmed hardware

| Part | Quantity | Known configuration | Still to verify |
|---|---:|---|---|
| ST NUCLEO-F401RE | 1 | STM32F401RE target; Zephyr board `nucleo_f401re`; team confirms external E5V power, JP5 on E5V, JP1 open; ST-LINK USB for flashing/debugging/serial | Board revision; post-change USB/serial verification |
| L298N dual H-bridge module | 1 | Driver for left and right DC motors; ENA/ENB and IN1–IN4 interfaces | Exact module/vendor, module schematic, 5 V regulator-jumper state, thermal/current limits for these motors |
| Left and right motor encoders | 2 | A/B quadrature signals; encoder VCC wired to Nucleo 3V3 and GND to GND; pin assignments in [STM32_PINOUT.md](STM32_PINOUT.md) | Model, rated supply/output circuitry, counts per wheel revolution, vehicle-forward signs; successful hand-turn tests |
| HW-688 DC-to-DC step-down buck converter module | 1 reported | Model/type confirmed by the user; used for 12 V to 5 V conversion feeding Nucleo E5V with a common ground; apply external power before connecting USB | Module vendor/revision and datasheet, output measured under load, continuous/peak rating, other attached loads |
| Laptop-to-Nucleo USB connection | 1 | ST-LINK programming and serial diagnostics; USB telemetry has been observed | Cable/board connection and current enumeration should be checked before each flash |

Last recorded L298N wiring report: ENA and ENB jumpers fitted, IN1–IN4 disconnected. These are historical observations, not an instruction for powered operation. Confirm the present state before testing. The proposed direction wiring and PWM jumper precautions live in [STM32_PINOUT.md](STM32_PINOUT.md).

## Handout baseline and incomplete specifications

| Part | Target quantity | Intended role | Missing team-specific detail |
|---|---:|---|---|
| Raspberry Pi 4, microSD, official USB-C supply | 1 set | Receive laptop UDP, bridge commands/status to the MCU | RAM variant, storage size, OS/setup and current network address |
| Logitech wheel, pedals, 24 V power brick | 1 set | Laptop cockpit input; wheel buttons provide self-test and turn signals | Exact wheel model, selected proxy, measured axes/button indices; consult the team results sheet |
| Car chassis and DC motors | 1 chassis, 2 motors | Drive and steering mechanics; motors have encoder feedback | Exact chassis/motor models, gear ratio, wheel diameter, rated voltage and stall current |
| Steering servo | 1 | Steer the linkage from an independently powered rail | Model, supply/current rating, accepted signal voltage, safe pulse endpoints and period |
| Current sensors | 3 | One per motor and one for the servo; telemetry only in Lab 2 | Models, ranges, supply voltage, output transfer functions and ADC-safe conditioning |
| Blinker LEDs and series resistors | 4 LED channels | Front/rear left/right signals | LED specifications, resistor values, polarity and any required driver circuitry |
| 12 V wall adapter and barrel-jack screw-terminal splitters | 1 supply; splitters as needed | Motor rail and converter input | Adapter current rating, polarity and actual distribution wiring |
| Buck converter and 5 V linear regulator | Kit baseline | Step-down power options listed in the handout; the team's buck converter is the HW-688 recorded above | Whether the linear regulator is installed at all |
| Breadboards, jumpers, 22 AWG solid wire | As needed | Subsystem wiring and labeled scope test points | Actual quantities and suitability of motor/power-current paths |
| USB/network/display accessories and tools | As needed | Pi setup, wired networking, assembly | Actual inventory; see the handout for the kit list |

The handout links a [Hiwonder Ackermann chassis](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503) for component information. Treat this as a reference until the team's exact chassis/motor/servo markings are checked. The included encoder motor controller mentioned there is not a substitute for the team's confirmed L298N module.

## Current power setup

The handout's baseline is 12 V to the H-bridge motor supply, stepped-down power to the servo, laptop USB to the Nucleo, and the Pi's own official supply to the Pi. Share signal ground where required; never power the Pi from the Nucleo or the Nucleo from the Pi. Motors and the servo are not powered by MCU GPIO or the Nucleo's sensor rails.

**Latest team-confirmed hookup:** the user chose external 5 V power for the Nucleo, with USB for flashing and debugging, and confirmed completing the procedure below. Converter positive now connects to **E5V**, converter ground to **GND**, **JP5 is on E5V**, and **JP1 is open**. External power is applied before USB. This is user-confirmed wiring, not an independently measured rail or post-change functional test.

This supersedes the earlier ordinary-5V/U5V hookup, which risked backfeeding, and the interim USB-only recommendation. No damage was reported from the earlier hookup.

For encoder-only bring-up, disconnect the **12 V feed to the L298N motor-power input**, with supplies off before changing wiring. Leave the converter branch available so it can power the Nucleo when the 12 V adapter is turned on. Keep common signal ground. Turning off the shared 12 V adapter would now also turn off the Nucleo; motor isolation must be separate from Nucleo power.

For the NUCLEO-F401RE, [ST UM1724 Rev 17, sections 7.5.2 and 7.5.4](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf#page=22) documents external 5 V plus USB communication as follows:

1. Disconnect both supplies before changing wiring or jumpers.
2. Use **E5V at CN7 pin 6**, rated **4.75–5.25 V**, with converter ground connected to board GND. ST lists 500 mA maximum for this input.
3. Set **JP5 to pins 2–3, E5V**, and remove **JP1**.
4. Apply external power first, check red **LD3**, then connect the laptop to ST-LINK USB **CN1** for communication/programming/debugging.

The ordinary **+5V header at CN6 pin 5 / CN7 pin 18** is documented as an output, not the E5V input used in that procedure. **VIN is a 7–12 V input**, not the destination for the converter's regulated 5 V. Do not infer safe wiring from the board continuing to run. Confirm physical pin numbering and board revision before changing anything.

The L298N module's 5 V regulator jumper is separate from its ENA/ENB jumpers and the Nucleo's JP5. Its power wiring must be checked against the actual module before attaching an external 5 V rail.

## Shared records

- [Team Google Drive folder](https://drive.google.com/drive/folders/1tPSb31DnQEuhYn843_J5W0746Dr3bdPd?usp=drive_link): shared project documents; contents are not mirrored or inventoried here.
- [Lab 2 Part 1 results and pin-planning sheet](https://docs.google.com/spreadsheets/d/1dooWs_u2aW8KV9ROrJsESd9B8kbxStf5QkPFaePCx2k/edit?gid=177898744#gid=177898744): team measurements and wiring plan.
- [Local pin assignments](STM32_PINOUT.md): electrical signal mapping, confirmed versus proposed wiring, and firmware integration issues.
- [Encoder-only bring-up](../bringup/encoder_test/README.md): toolchain, flashing, test commands, and recorded results.

When a part is identified, record its exact marking/model, relevant datasheet, electrical limits, and confirmation source here. Keep unknowns explicit rather than adopting a plausible part from a generic kit list.
