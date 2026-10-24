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

## Encoder and output interfaces

U81 is SN74LVC14APWR powered at 3.3V. Its inputs accept up to 5.5V; its outputs
stay in the MCU domain. Four Schmitt-trigger channels condition the encoders;
100-ohm series resistors and 10k pullups support a proposed 5V/open-collector
interface. Actual encoder supply/output type still needs confirmation. Both A
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
| J82/J83 encoders | 5.1V | GND | A raw | B raw |
| J90 servo | GND | sensed 6.6V | PWM | |
| J550/J551/J650/J651 LEDs | series-resistor positive | switched negative | | |

These are board pin numbers, not inferred cable colors. Verify the cable pinout
before making adapters or applying power.

## Clock and ordering-code corrections

Six CX3225SB16000H0FLJCC crystals have a 12pF specified load. Equal 18pF C0G
capacitors give 9pF series capacitance; we assume another 3pF effective stray
capacitance. This is a layout-dependent starting value, to check after routing.
[Kyocera specification](https://www.mouser.com/datasheet/2/40/knsk_s_a0010201031_1-2585733.pdf).
We use TI's documented SN65HVD231DR SOIC-8 order code; the earlier
SN65HVD231MDREP string could not be verified. The October 23 v3 course list
explicitly identifies SN65HVD231DR; that stock identity is now resolved.
[TI orderable part](https://www.ti.com/product/SN65HVD231/part-details/SN65HVD231DR).
