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
| Hiwonder Ackermann steering chassis kit | 1 | [Exact kit link confirmed by the user](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503), including its motors and steering servo; team uses an L298N motor driver | Installed servo marking; motor model is confirmed below |
| JGB37-520R30-12 DC gearmotors | 2 | User-confirmed highlighted model in the [specification image](assets/JGB37-520R30-12-spec.png); 12 V, 1:30, 280 RPM rated, 320 RPM no-load, 3.2 A stall; L298N drive; both-motor 55% starts and 40% four-second holds after a 60% kick passed 3/3 at 10 kHz with raised wheels; user reports 75 mm wheel diameter | Loaded rolling circumference; 51–54% startup and 36–39% holding duties, ground load, long-term holding and current/thermal margins remain unverified; see [measurements](MOTOR_CHARACTERIZATION.md) |
| Makerfabs ACS712 Current Sensor- 5A | 3 target | [Exact product confirmed by the user](https://www.makerfabs.com/acs712-current-sensor-5a.html), SKU MSE71205A; nominal -5 to +5 A, 5 V supply, 185 mV/A, 2.5 V at zero current; intended for left motor, right motor and servo telemetry only | Physical quantity, board revision/chip markings, measured supply/offset/sensitivity and actual wiring; user selected direct ADC connection; signed upper-rail endpoints are documented below |
| Left and right motor encoders | 2 | Built into JGB37-520R30-12; specification lists A/B, 11 magnetic-ring lines, 3.3–5 V and built-in pull-up shaping; encoder VCC wired to Nucleo 3V3 and GND to GND; both hand-turn tests passed; forward raw counts decrease on the left and increase on the right; one turn measured 1319 left / 1327 right absolute counts; use validated 1320 counts/rev at x4; see [calibration record](ENCODER_SPEC.md) | Detailed output circuitry, refined multi-revolution calibration, powered-speed accuracy |
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

## Confirmed motor specifications

The user identified both motors as **JGB37-520R30-12**, the red-highlighted
column in the supplied [specification image](assets/JGB37-520R30-12-spec.png).
The image is retained as the source; its original page URL was not supplied.
These are published specifications, not team measurements.

| Property | JGB37-520R30-12 specification |
|---|---|
| Motor type | Permanent-magnet brushed DC gearmotor |
| Rated voltage | 12 V |
| Gear ratio | 1:30 |
| No-load / rated speed | 320 / 280 RPM |
| Stall / rated torque | 5.8 / 1.2 kg·cm, as labeled in the source |
| Stall / rated current | 3.2 / 0.36 A |
| Rated power | About 7 W, as listed |
| Encoder | A/B quadrature; 11 magnetic-ring lines; built-in pull-up shaping |
| Encoder supply | 3.3–5 V |
| Output shaft | 6 mm diameter, D-type eccentric shaft |
| Connector | PH2.0-6PIN |
| Motor weight | 152 ± 1 g |

The image recommends 12 V and lists an 11–16 V motor-supply range. This does
not change the team's 12 V supply or establish a range for the other components.
Its approximate 7 W entry is transcribed unchanged; 12 V × 0.36 A is 4.32 W,
so those entries should not be treated as a consistent measured operating point.

This identification supersedes using the generic chassis listing's 85 RPM
rated / 110 RPM no-load figures for these motors. Keep the user-selected
**300 RPM full-throttle target** and bench-validated **1320 counts/revolution**.
The measured full-duty average remains **316.59 RPM**. Neither a published
speed nor a gear ratio replaces that measurement. See
[encoder calibration](ENCODER_SPEC.md) and [motor measurements](MOTOR_CHARACTERIZATION.md).
The 3.2 A per-motor stall specification does not establish that the shared
12 V / 2 A adapter or L298N module can support a stall; their margins remain
unverified. No control limits or firmware changed with this identification.

## ACS712 current sensor identification

**2026-09-28 inventory update:** the user now has a third module and confirmed
its ACS712-05B / 5 A marking. The user subsequently reported the third sensor
connected and the system powered again following the PA1/A1 wiring plan.
This is a user-reported installation, not independent wiring inspection.
The later mask-7 firmware flash passed idle acquisition on all three channels;
zero-current calibration and load-current validation remain pending. See the
[current-sensing record](CURRENT_SENSOR_HANDOFF.md).

The user confirmed the exact [Makerfabs ACS712 Current Sensor- 5A](https://www.makerfabs.com/acs712-current-sensor-5a.html),
SKU **MSE71205A**. The product page was read for this update. This replaces
the earlier family-only identification; the previously supplied Seeed guide
was only an example, not the team's exact module reference.

| Property | Makerfabs published specification |
|---|---|
| Measurement range | -5 to +5 A, bidirectional |
| Sensor supply | 5 V |
| Nominal sensitivity | 185 mV/A |
| Nominal zero-current output | 2.5 V |
| Output rise time | 5 us for a current step |
| Bandwidth | 80 kHz |
| Total output error | 1.5% at 25 °C |

The page also links an [ACS712 datasheet](https://www.makerfabs.com/desfile/files/ACS712-Datasheet.pdf).
The values above are product-page specifications, not measurements of our boards.
Physical quantity, board revision, chip markings and terminal orientation have
not been independently inspected.

Using the nominal values, `Vout = 2.5 V + I * 0.185 V/A`, so -5 to +5 A
corresponds to **1.575–3.425 V** at the sensor output. The upper end exceeds
the Nucleo's nominal 3.3 V ADC conversion range, but not the **4.0 V analog
absolute maximum** in [ST DS10086 Rev 4, Table 11 note 2](https://download.mikroe.com/documents/datasheets/erp/STM32F401RE.pdf#page=58).
Absolute maximum is a stress rating, not a guaranteed operating range.

The user subsequently selected **direct ADC connection without a divider**,
accepting clipping and selecting **4.320 A** as the upper-ADC-rail endpoint
magnitude. After the user's motor-orientation correction, upper-rail clipping
reports -4320 mA for motors and +4320 mA for servo. Falling-voltage readings have
no symmetric 4.320 A cap. See the conversion contract in
[Part 3.5](CURRENT_SENSOR_HANDOFF.md). This
supersedes the earlier divider proposal, not the 5 V sensor supply or common
ground requirement. Software clipping does not protect against voltage spikes
or unsafe power sequencing. Actual supply, offset, sensitivity and wiring
still require bench verification.

The root link application now acquires all three channels with nominal
calibration, batch averaging and read-only status/USB diagnostics. The standalone
motor-bench application is unchanged. Failed/stale acquisition is unavailable,
not zero; a ceiling reading is not an exact overrange measurement. See
[Part 3.5 implementation and bench checklist](CURRENT_SENSOR_HANDOFF.md).
The planned ADC assignments remain in [STM32_PINOUT.md](STM32_PINOUT.md).
During current-sensor debugging on 2026-09-28, the user confirmed sensor outputs
are connected to **A0 and A3**, not A1. This confirms the reported input pins,
not sensor identity, supply/ground wiring, measured output voltage or calibration.
The GUI labels these channels Left motor and Servo; its Right motor/A1 channel
is presently unconnected and any numeric reading there is not usable current.
An ADC validity bit alone does not detect this disconnected input. At the
user's request, the GUI now defaults to left/A0 and servo/A3 only, emits one
startup error for disconnected right/A1 and excludes it from chart values,
traces and scale. Raw capture still retains the ADC field. This does not change
firmware sampling or calibration; see [GUI telemetry](GUI_TELEMETRY.md).
The user subsequently identified missing sensor grounds and confirmed connecting
them. Before that correction, the module OUT pins measured 3.824 V and 3.695 V
relative to **Nucleo GND**, not the respective module GND. Those readings had an
unverified ground reference and must not be treated as calibrated sensor outputs.
The user also reported supplies around 5.22 V; post-correction supply, zero
offset and ADC reference still need measurement.

A passive capture after grounding (`logs/current-sense/console-20260928-002435.log`)
recorded 31 fresh samples, validity 7, error 0 and age 2..20 ms with LINK_OK,
zero propulsive duty and stationary encoder counts. Nominally converted A0
readings were 577..782 mA, mean 680.1; A3 were 814..1047 mA, mean 899.1. Neither
was clipped. These are uncalibrated readings, not accepted physical currents.
A1 remained unconnected and its negative readings are not usable current.
The earlier firmware acquisition stall was separately fixed; see
[ADC diagnosis](CURRENT_ADC_DIAGNOSIS.md).
This software change does not verify electrical correctness or calibration,
and adds no overcurrent protection.

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
