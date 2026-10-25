# Actuator circuit review

23 October 2026. These circuits are connected in the schematic and included in
the unrouted placement. We have not powered or tested the new PCB.

## Motor stage

U80 is the course L298N substitution. Its VS pin uses protected battery power;
VSS uses 5.1V. Local 100nF capacitors bypass both supplies, and C802 provides a
proposed 470uF/25V motor bulk capacitor. Each output has one SK520B diode to
protected battery and one from ground. U2/U3 remain in series with one lead of
each motor, so they measure winding current in either direction. The other
motor lead returns to the other bridge output, not ground.

The MCU enables and direction signals retain reset pulldowns. Enable HIGH with
equal direction inputs commands dynamic braking; enable LOW commands coasting.
The sense pins currently connect to power ground, following the unregulated
bridge arrangement. **No autonomous motor current limiter is implemented.**
The existing filtered ADC channels are measurement inputs, not a demonstrated
fast protection system. Nor is a main pack fuse a 2A-per-motor limiter.

ST specifies a 2A absolute DC limit per bridge and a 2A braking limit. The
handout's 3.2A motor stall value is not normal running current. We keep the
course driver and verify cooling and the course's expected brief-stall/protection
behavior. Lab 2 operation does not qualify sustained stalls on a new PCB.
At 1A per motor, the datasheet's 3.2V maximum bridge drop gives up to 6.4W for
two motors, before other losses. At 2A each, 4.9V maximum gives 19.6W. A heatsink
choice must be based on the agreed continuous current, ambient, case interface
and thermal resistance; we have not qualified sustained stalls.
[ST L298 datasheet](https://www.st.com/resource/en/datasheet/l298.pdf).

For the October 24 preliminary review, the team relays that Anson accepted
the proposed 6396BG heatsink and confirmed that motor stall current and
L298 loss/temperature measurements are not needed today. He will investigate
the mounting hardware. We keep the heatsink selection and record its attachment
as a staff follow-up before assembly. This does not establish tested cooling,
a safe stall duration or a per-motor current limit; see Current-evidence.md.

## Encoder and output interfaces

U81 is SN74LVC14APWR powered at 3.3V. Its inputs accept up to 5.5V; its outputs
stay in the MCU domain. Four Schmitt-trigger channels condition the encoders;
100-ohm series resistors and 10k pullups use the 3.3V logic domain.
J82/J83 now supply the encoders from that same nominal 3.3V rail (3.318V
calculated setpoint), replacing the incompatible nominal 5.1V connection.
The recorded JGB37-520 specification gives 3.3-5V; the earlier Lab 2 setup
used the Nucleo 3.3V supply. Actual rail tolerance, output type and signal
quality still need verification; this is a schematic correction, not a new test. Both A
and B invert, preserving quadrature phase order; firmware must verify initial
state, sign and counts. Unused logic inputs are grounded.
[TI SN74LVC14A datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc14a.pdf).

J90 takes its 6.6V supply after the servo shunt, with ground and PWM on separate
pins. We propose rated Hirose DF63M connectors for battery, motor power and
servo rather than placing motor/servo current on an unspecified signal header.
These require adapter harnesses; they are not asserted to mate with existing
vehicle plugs. Encoder connectors carry only supply, ground, A and B.
The DF63M-2P header is rated 14A; the selected wire/contact/derating and fuse
must also support the agreed load. [Hirose](https://www.hirose.com/en/product/p/CL0680-0567-0-00).

Four MMBT3904 low-side stages drive external vehicle LEDs. Each has a 2.2k base
resistor, 100k base pulldown and 220-ohm LED series resistor from 5.1V. For a 2V
LED and 0.2V saturated transistor, current is about 13mA; a 3V LED gives about
8.6mA. Verify actual LED forward voltage and polarity. These are not lamp drivers
for incandescent bulbs or high-power LED modules.

## Connector pin definitions

| Reference | Pin 1 | Pin 2 | Pin 3 | Pin 4 |
|---|---|---|---|---|
| J40 battery | Battery + | GND | | |
| J80 left motor | ACS712 output to motor | L298 OUT2 | | |
| J81 right motor | ACS712 output to motor | L298 OUT4 | | |
| J82/J83 encoders | nominal 3.3V logic rail | GND | A raw | B raw |
| J90 servo | GND | sensed 6.6V | PWM | |
| J550/J551/J650/J651 LEDs | series-resistor positive | switched negative | | |

These are board pin numbers, not inferred cable colors. Verify the cable pinout
before making adapters or applying power.

### October 24 servo cable identification

The October 24 team photos show a three-position servo cable with white,
red and black wires. In the close-up showing the contact-retention windows
and the servo cable exiting downward, their left-to-right order is white,
red, black. The accompanying team report identifies white as signal, red
as the existing setup's 5V supply, and black as ground. Photo collection and
the reported wire-function identification are complete; no continuity test
or wire-gauge measurement was supplied.

Our planned adapter maps black to J90 pin 1 (GND), red to pin 2 (sensed servo
supply), and white to pin 3 (PWM). J90's planned supply is 6.6V; the reported
5V bench connection describes the old setup. Hiwonder's
[LD-1501MG specification](https://www.hiwonder.com/products/ackermann-steering-chassis)
gives a 6-8.4V working range, so 6.6V is a supported nominal design choice.
We have not measured the new rail's tolerance, ripple or overshoot.
The pictured plug does not directly mate with
the selected 3.96mm Hirose J90 connector. Exact servo-side pitch/keying, wire
size and the finished adapter's end-to-end continuity remain to be checked.
Do not assign connector pin numbers from photographic left/right alone;
the view reverses when looking into the mating face.

For the October 24 schematic/BOM review, we record the adapter design and
unresolved sourcing/fit. Physical mating checks precede connector purchasing;
finished-harness continuity checks precede first power after assembly. A
completed harness is not claimed as part of this preliminary submission.

The permitted-source candidate is SparkFun19224 (ROB-19224),
[DigiKey1568-19224-ND](https://www.digikey.com/en/products/detail/sparkfun-electronics/19224/16511100).
It is not a finalized selection: the manufacturer documents 26AWG and a
2.54mm JR-FU male interface, but no cable/contact current rating. See
[Parts-review.md](Parts-review.md) for the remaining review question.

If qualified, preserve its shrouded servo-mating end and adapt its individual
tails to 22AWG wire, then DF63A-2022SC contacts in DF63-3S-3.96C. Do not put
26AWG directly in a 20-22AWG crimp. The conditional end-to-end map is:

| Existing servo function | SparkFun P1 in its drawing | PCB J90 |
|---|---|---|
| White / PWM | 1 / yellow | 3 / PWM |
| Red / supply | 2 / red | 2 / sensed6.6V |
| Black / ground | 3 / brown | 1 / GND |

These P1 numbers come from the manufacturer's drawing, not from the team's
photo orientation. Confirm each conductor by continuity with power off;
do not copy donor colors onto the PCB pin order. Keep every splice separately
insulated and strain relieved, and verify that the servo cannot be plugged
in backwards. Changing wire size does not qualify the original contacts or
the donor's 26AWG section. This is an assembly plan, not an assembled harness.

### October 24 motor/encoder cable identification

The October 24 team photo and accompanying report give the following order
for the pictured six-position harness. Positions run top to bottom in that
photo; they are not manufacturer cavity numbers. Colors refer to the attached
jumper wires on the right, not the black motor-side ribbon cable.

| Photo position | Jumper color | Reported function | Planned PCB adapter destination |
|---|---|---|---|
| Top / 1 | Red | Motor lead 1 (+ reference) | J80 or J81 pin 1 |
| 2 | Orange | Encoder positive supply (VCC) | J82 or J83 pin 1; nominal 3.3V |
| 3 | Yellow | Encoder phase A | J82 or J83 pin 3 |
| 4 | Blue | Encoder phase B | J82 or J83 pin 4 |
| 5 | Gray | Encoder ground | J82 or J83 pin 2 |
| Bottom / 6 | Black | Motor lead 2 | J80 or J81 pin 2 |

Use J80/J82 together for the left motor and J81/J83 for the right motor.
Black motor lead 2 is not encoder ground: both motor leads connect to the
H-bridge output path, which reverses their relative polarity for direction.
The (+) reference does not establish vehicle-forward rotation; confirm the
left/right direction and encoder sign during bring-up.

Photo collection and the reported order for this harness are complete.
We have not inferred the second harness's order, exact mating geometry,
wire gauge or tested adapter continuity from this photo. Check those when
preparing the adapters. The encoder supply specification is 3.3-5V. The October 24 design revision
connects both encoder supply pins to the existing nominal 3.3V logic rail.
Only J82.1 and J83.1 changed net; pull-ups were already on that rail.

## Clock and ordering-code corrections

Six CX3225SB16000H0FLJCC crystals have a 12pF specified load. Equal 18pF C0G
capacitors give 9pF series capacitance; we assume another 3pF effective stray
capacitance. This is a layout-dependent starting value, to check after routing.
[Kyocera specification](https://www.mouser.com/datasheet/2/40/knsk_s_a0010201031_1-2585733.pdf).
We use TI's documented SN65HVD231DR SOIC-8 order code; the earlier
SN65HVD231MDREP string could not be verified. The October 23 v3 course list
explicitly identifies SN65HVD231DR; that stock identity is now resolved.
[TI orderable part](https://www.ti.com/product/SN65HVD231/part-details/SN65HVD231DR).

## October 24 servo current lookup

The exact-model [Hiwonder chassis specification](https://www.hiwonder.com/products/ackermann-steering-chassis)
lists LD-1501MG no-load current100mA and stall current2.4-3A. The100mA value
is a catalog reference; its voltage and static-hold/unloaded-motion condition
are unspecified. It does not establish calibrated holding current at6.6V.
Our10mOhm/gain50 circuit gives50mV output at100mA,1.5V at3A, and0.09W shunt
dissipation at3A. The nominal20mA resolution target gives about12.4 ideal ADC
counts at3.3V/12-bit. These arithmetic checks support retaining the selected
shunt/gain for review; physical noise, offset and calibration remain open.
See Current-evidence.md and Power-calculations.json for assumptions and sources.
