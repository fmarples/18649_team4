# Team hardware BOM and power setup

**Integration calibration record:** Tianyi selected left 1200 us, center
1600 us and right 2000 us for the steering linkage. These are tracked in
`config/servo_calibration.json`; loading them does not enable PWM. The user
reported smaller wheel-angle increments near the end of travel and subsequently
confirmed Parts 3.3 and 3.4 tested individually. No exact angle or waveform
measurements were supplied with that confirmation. Combined-board
power/wiring and simultaneous motor/servo operation remain unverified. This
record does not confirm the previously discussed shared-converter hookup.

This is a working BOM, not a completed purchasing list or an as-built schematic. The [Lab 2 handout](18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf), especially "What is in the kit" and Parts 3 and 5, supplies the baseline. Team confirmations refine it below. Quantities marked "target" come from the assignment, not a physical inventory.

## Team-confirmed hardware

| Part | Quantity | Known configuration | Still to verify |
|---|---:|---|---|
| ST NUCLEO-F401RE | 1 | STM32F401RE target; Zephyr board `nucleo_f401re`; team confirms external E5V power, JP5 on E5V, JP1 open; ST-LINK USB for flashing/debugging/serial | Board revision; post-change USB/serial verification |
| L298N dual H-bridge module | 1 | Driver for left and right DC motors; ENA/ENB jumpers removed; separate 5V-EN regulator jumper installed; user measured +5V terminal to GND at 5 V with a multimeter | Exact module/vendor, module schematic, motor rail/output voltage under load, thermal/current limits for these motors |
| Hiwonder Ackermann steering chassis kit | 1 | [Exact kit link confirmed by the user](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503), including its motors and steering servo; team uses an L298N motor driver | Installed motor/servo markings and their electrical/mechanical ratings |
| Left and right DC gearmotors | 2 | Included with confirmed Hiwonder chassis; L298N drive; with both motors together, 55% starts passed 3/3 and 40% four-second holds after a 60% kick passed 3/3, at 10 kHz with raised wheels; user reports 75 mm wheel diameter | Exact motor markings, gear ratio, rated voltage/stall current, loaded rolling circumference; 51–54% startup and 36–39% holding duties, ground load, long-term holding and current/thermal limits remain unverified; see [measurements](MOTOR_CHARACTERIZATION.md) |
| ACS712 current sensor board | 3 target | Board family confirmed by the user; intended for left motor, right motor and servo current telemetry only; example reference below is not the purchase source or an exact board identification | Physical quantity, chip suffix/current range, board vendor/revision, supply voltage, zero-current offset, sensitivity, output range, ADC-safe conditioning and actual wiring |
| Left and right motor encoders | 2 | A/B quadrature signals; encoder VCC wired to Nucleo 3V3 and GND to GND; both hand-turn tests passed; forward raw counts decrease on the left and increase on the right; one turn measured 1319 left / 1327 right absolute counts, supporting provisional 1320 counts/rev at x4; see [calibration record](ENCODER_SPEC.md) | Model, rated supply/output circuitry, refined multi-revolution calibration, powered-speed accuracy |
| HW-688 DC-to-DC step-down buck converter module | 2 reported | First supplies 5 V to Nucleo E5V. Second photo-identified: fixed nominal 5 V, VIN+/VIN- input beside barrel jack, 5V/GND output beside USB, no adjustment potentiometer. User reports TA said use 5 V for the servo; the second converter is now selected for that bench plan. | Actual output voltage under no-load/load, continuous/peak current rating, thermal performance and servo operation at 5 V remain unmeasured |
| Laptop-to-Nucleo USB connection | 1 | ST-LINK programming and serial diagnostics; USB telemetry has been observed | Cable/board connection and current enumeration should be checked before each flash |

Latest L298N wiring report: the user confirmed all six control wires connected per [STM32_PINOUT.md](STM32_PINOUT.md), with **ENA/ENB jumper caps removed**, and described the chassis as supported with driven wheels clear. This supersedes the earlier jumpers-fitted/IN1–IN4-disconnected report. Physical wiring remains uninspected. The user confirmed the separate 5 V regulator jumper is installed and measured the driver's +5V terminal relative to GND at **5 V** with a multimeter. Standalone [motor-test firmware](../bringup/motor_test/README.md) was flashed and its idle serial check passed: zero duty and all six MCU control-pin readbacks low. Subsequent separate 20%-duty, nominal 500 ms commands returned to disabled without firmware faults, but **neither wheel moved and a beep was heard**, per the user. The subsequent 35% trial also produced only a beep with no movement, per the user. A subsequent left-only 50% / 500 ms trial also failed to move the wheel. The user measured **12 V across unloaded OUT1–OUT2** during a left-only 100% / 3-second diagnostic, and **3.2 ohms across the disconnected left motor's power leads** with power off. These establish unloaded DC output and motor-circuit continuity, not loaded operation or motor health. The logic rail is user-measured at 5 V; motor rail/output voltage under load, startup behavior, and current/thermal limits remain unvalidated. The left motor was reconnected and bounded LEFT-only 50% / 1000 ms firmware flashed, replacing the unloaded diagnostic. The L298N input measured 12 V idle; one supply-sag measurement pulse returned to disabled without observed firmware faults/reset. On a repeat pulse, the user reported no apparent input-voltage drop and no wheel movement. Sustained supply sag is therefore less supported, though the slow meter cannot exclude brief transients. Loaded OUT1–OUT2 again displayed approximately 0.3 V at 50% / 1000 ms. Separate 100% / 200 ms LEFT and RIGHT kicks verified channel identity and polarity using both encoders, without invalid transitions, GPIO errors or firmware faults. Positive bridge polarity drives LEFT backward (also visually confirmed) and RIGHT forward. The subsequent five-second diagnostic corrected left polarity and permitted LEFT, RIGHT or BOTH forward at 100%, with a latched 150 ms per-wheel no-progress/reversal guard and encoder-error checks. That profile has since been replaced by the short-pulse startup diagnostic below. The user explicitly selected simultaneous operation despite the shared 2 A supply limit. One 5-second BOTH-forward trial passed, with zero reported encoder/firmware errors, then disabled both outputs; wheels coasted afterward. A subsequent thread-priority correction was flashed and idle-checked only, without repeating the trial. See the pin document for direction settings and the motor-test README for evidence/limits. The software guard is not current limiting; long-term/ground-loaded operation and electrical/thermal limits remain unverified. The proposed 1 kHz experiment was not implemented; the timer configuration remains 10 kHz (full duty is steady enable).

### Startup sweep, 2026-09-27

With raised wheels and unchanged wiring reconfirmed by the user, both motors were
tested separately, forward from rest, at 10 kHz with a 200 ms pulse cap and the
existing 150 ms motion guard. **50% failed on both; 55% passed 3/3 starts per motor;
60% passed 1/1 per motor.** The user also confirmed movement at 60%. The 50%
failures produced only 1–2 forward encoder counts before the guard latched the
selected-wheel stall fault. Every trial ended disabled and stationary, with no
invalid transitions or GPIO errors. Deliberate reflashes cleared faults between
trials; no automatic duty escalation or retry was used.

The user subsequently required **both motors together**, superseding separate-wheel
measurements as the operating case, and authorized one-command sequencing with
verified reflash/reset after expected stall faults only. The complete simultaneous
batch confirmed **55% startup, 3/3**, while 50% failed. With a 60% / 200 ms kick,
**40% held both motors for 4 seconds, 3/3**; at 35%, the left stalled after about
2.6 seconds and the guard stopped both. No wiring changed. See
[simultaneous speed measurements and evidence](MOTOR_CHARACTERIZATION.md).

These are lowest tested passing duties, not exact or universal minima. 51–54%
startup and 36–39% holding duties remain untested. Ground-loaded performance,
long-term holding, current and thermal margins remain unverified. The current
flashed diagnostic supports 60% / 200 ms startup pulses and a separate two-stage
60% / 200 ms kick followed by 55% / maximum 4000 ms hold. Those fixed-duty modes
retain their motion guards.
The sweep's final reflash was idle-checked only; outputs disabled and encoders stationary.
A later user-authorized PID image and single BOTH-wheel 45 RPM test passed the
provisional speed tolerance, averaging 44.09 RPM over the last powered second.
Both outputs then disabled and counts became stationary with no faults. The
current image retains the startup/holding profiles and now runs continuous PID
with B1 stop and user-selected startup/sustaining thresholds; wiring
and power are unchanged. See the [PID record](MOTOR_CHARACTERIZATION.md#first-bounded-pid-trial).
This does not establish current/thermal margins or loaded performance.

## Handout baseline and incomplete specifications

**Servo source verification, 2026-09-26:** the exact Hiwonder kit page lists
LD-1501MG, 6–8.4 V, 500–2500 us, 2.4–3 A stall current. Its STM32 tutorial
specifies 20 ms/50 Hz. Actual installed marking, separate supply, 3.3 V signal
acceptance and safe linkage endpoints still need verification. See the exact kit source linked in the BOM and the steering evidence record. Do not raise the converter powering Nucleo E5V above 5 V.

**Separate blinker bench (Tianyi, 2026-09-26):** another NUCLEO-F401RE with
red front-left, yellow rear-left, white front-right and blue rear-right LEDs.
Each uses a 470-ohm resistor to GND; see the pin document. User reports all four
wired and Pi UART/wheel available. No oscilloscope or logic analyzer currently
available. This board's power setup is not independently confirmed and should
not be assumed to match the motor bench's E5V arrangement.

| Part | Target quantity | Intended role | Missing team-specific detail |
|---|---:|---|---|
| Raspberry Pi 4, microSD, official USB-C supply | 1 set | Receive laptop UDP, bridge commands/status to the MCU | RAM variant, storage size, OS/setup and current network address |
| Logitech G920 wheel, pedals, 24 V power brick | 1 set | G920 and Windows course proxy reported in Tianyi's [Part 2 bring-up record](../README.md); wheel buttons provide self-test and turn signals | Final vehicle-function button assignments; consult the team results sheet |
| Steering servo | 1 | Included with the team-confirmed Hiwonder kit; steer the linkage from an independently powered rail | Exact servo marking, supply/current rating, accepted signal voltage, safe pulse endpoints and period |
| Blinker LEDs and series resistors | 4 LED channels | Front/rear left/right signals | LED specifications, resistor values, polarity and any required driver circuitry |
| 12 V wall adapter and barrel-jack screw-terminal splitters | 1 supply; splitters as needed | Motor rail and converter input; user reports adapter label **12 V, 2 A output** | Actual voltage under motor-start load, overload behavior, polarity and distribution wiring |
| Buck converter and 5 V linear regulator | Kit baseline | Step-down power options listed in the handout; the team's buck converter is the HW-688 recorded above | Whether the linear regulator is installed at all |
| Breadboards, jumpers, 22 AWG solid wire | As needed | Subsystem wiring and labeled scope test points | Actual quantities and suitability of motor/power-current paths |
| USB/network/display accessories and tools | As needed | Pi setup, wired networking, assembly | Actual inventory; see the handout for the kit list |

The user confirmed that this [Hiwonder Ackermann steering chassis kit](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503) is the team's car kit, including the motors and steering servo. Use that exact variant link when checking component information, then verify the installed component markings before adopting ratings or calibration values. The included encoder motor controller mentioned in the handout is not a substitute for the team's confirmed L298N module.

## ACS712 current sensor identification

The user confirmed that the team uses an **ACS712 current sensor board** and
provided this [Seeed Studio ACS712 guide](https://www.seeedstudio.com/blog/2020/02/15/acs712-current-sensor-features-how-it-works-arduino-guide/)
as an example of a similar board. It is not the team's purchase source, and the
exact module has not been matched to that example. Do not adopt a current range,
sensitivity or pinout from the example without checking the installed board.

Record the chip suffix and board markings before choosing the ADC conversion
constants. Verify the sensor supply, zero-current output, sensitivity and full
output-voltage range, then check any required conditioning against the Nucleo's
ADC input limits before connecting the signal. The planned ADC assignments are
in [STM32_PINOUT.md](STM32_PINOUT.md); the model confirmation does not establish
that those connections are wired or tested. Current sensing remains unintegrated
in the link and motor-bench applications and does not provide overcurrent protection.

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
