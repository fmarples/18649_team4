# Power margins, capacitors and thermal review

27 October 2026. We recalculated these margins after widening existing
3.3 V and 5 V traces. Setpoints and BOM are unchanged in this pass. The
calculations identify limits of the present design; they do not
qualify it for fabrication. [Power-margin-check.json](Power-margin-check.json)
records the source hashes, assumptions and numerical results. The existing
8–15 V input envelope makes this work useful before the battery is selected.

## Voltage available at the loads

The source corners include reference and divider tolerances. We subtract the
shared-current tree drops from [Supply-path-review.md](Supply-path-review.md).
That model counts whole trace segments and assigns the Pi current to one
power pin, so it can overstate positive-feed loss. It omits ground, contact,
heating and dynamic losses, so its result is not a guaranteed lower bound.

| Load | Static source minimum | Positive-feed drop | Calculated load voltage before other losses | Comparison |
| --- | ---: | ---: | ---: | --- |
| Worst CAN transceiver, U25 | 3.2629 V | 0.0949 V | 3.1680 V | 0.1680 V above its 3.0 V minimum |
| Worst encoder connector, J82 | 3.2629 V | 0.0932 V | 3.1697 V | 0.1303 V below the recorded 3.3 V range endpoint |
| Pi, J70 | 5.0146 V | 0.1498 V | 4.8648 V | Only 0.0033 V above the upper corner of its low-voltage detector |

The CAN comparison uses the [SN65HVD231 operating limit](https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf).
The [recorded motor specification](../doc/HARDWARE.md) gives the encoder supply
as 3.3–5 V without endpoint tolerance. Earlier operation from nominal 3.3 V
does not establish operation at 3.17 V. Even eliminating all trace drop would
leave the present source low corner below 3.3 V. Thus widening copper alone
does not close this encoder specification question.

[Raspberry Pi documents](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
a 4.63 V ±5% low-voltage detector: its upper corner is 4.8615 V. This is a
warning threshold, not a minimum operating specification or proof of failure.
The present screen cannot guarantee warning-free operation at the full 3 A
allocation.

Multiplying conductor resistance by an assumed 1.45 and reserving 50 mV for
return loss gives 3.075 V at U25 and 4.747 V at J70. The multiplier represents
approximately 60 °C copper and 20% width reduction; it is not a complete
manufacturing or temperature bound. A nominal 15.2 µm copper sheet has about
1.13 milliohms per square. A hypothetical five-square path at 3 A loses
17 mV; the real plane's apertures, spreading and shared currents determine its
loss. This example is not a ground-plane extraction.

The subsequent [ground-plane screen](Ground-plane-review.md) extracts the
saved In1 fill and balances shared DC currents in three scenarios. Positive
Pi ground offsets are about 2.6–6.5 mV over its mesh/port sweep. Local tracks,
spokes, barrels and contacts remain excluded; the 50 mV allowance above is
still an assumption, not a measured or simulated total-return bound.
The new review also separates contact-resistance sensitivity from an actual
connector specification. The full Pi/encoder voltage decisions remain open.

**Design decision:** the latest copper refinement reduces the worst logic
feed drop by about 34% and the Pi feed drop by about 6% in the same model.
It does not close the full voltage budget. Before release, include ground,
contact and regulator load/line behavior in the assessment; improve the Pi
feed further if required. Establish the encoder's actual allowed range or select a
separate supply within its documented range. Do not raise the common logic
voltage blindly, or move encoders directly to the existing 5 V rail: that
rail's static upper corner is 5.186 V. The [SN74LVC14A](https://www.ti.com/lit/ds/symlink/sn74lvc14a.pdf)
accepts inputs up to 5.5 V, but that does not set the encoder's supply limit.

## Effective capacitance and ripple

Each output has two GRM219R61C226ME15L 22 µF, ±20%, 16 V X5R parts.
Their combined nominal 44 µF becomes 29.92 µF after applying −20% tolerance
and −15% temperature variation, before bias and aging. Each input's
GRM32ER61E226KE15L is 22 µF, ±10%, 25 V X5R; the corresponding value is
16.83 µF. These multiplicative screens are assumptions, not guaranteed
combined limits from a part approval specification.
See the manufacturer sheets for the [output part](https://www.mouser.com/datasheet/2/281/1/GRM219R61C226ME15_01A-1986409.pdf)
and [input part](https://www.farnell.com/datasheets/4088151.pdf).

| Conditional design target | Required effective capacitance | Retention after the tolerance/temperature screen |
| --- | ---: | ---: |
| Output LC pole at 20 kHz, L = 3.76 µH | 16.84 µF total | 56.3% of 29.92 µF |
| Same target with L = 2.63 µH | 24.08 µF total | 80.5% of 29.92 µF |
| Input decoupling above 10 µF | More than 10 µF | More than 59.4% of 16.83 µF |

The first inductance includes the selected 4.7 µH part's −20% tolerance.
The second is [Eaton's full-load minimum at 6.7 A and 25 °C](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf).
Using it at our loads is a sensitivity to magnetic rolloff, not a guaranteed
minimum at all temperatures. The LC target follows the
[TPS564252 design guidance](https://www.ti.com/lit/ds/symlink/tps564252.pdf);
20 kHz is not a pass/fail stability boundary.

The exact selected parts' bias/aging curves were not retrievable in this
review. Their nominal value and voltage rating do not establish retention.
Required data are effective C/ESR at approximately 3.37, 5.19 and 6.82 V
for the output parts and up to 15 V for the inputs, with the applicable
temperature/aging conditions. [Murata SimSurfing](https://www.murata.com/en-global/tool/simsurfing)
is the manufacturer data source; a generic X5R curve is not a substitute.
If exact data cannot support these targets, choose a documented replacement
or additional capacitance and update the affected footprints/BOM.

The sensitivity grid gives input-capacitor ripple up to 2.107/1.719/0.464 A
RMS and combined output-capacitor ripple up to 1.021/0.931/0.461 A RMS for
servo/5 V/logic. These are valid continuous-current model cases only, not
component ratings or guaranteed maxima. Two parallel capacitors do not
necessarily share equally. The selected parts' ESR and heating data are still
needed; an example capacitor's ripple rating in TI's application circuit
cannot be assigned to ours. X5R's 85 °C upper operating temperature also
limits the local capacitor temperature, even if a nearby IC allows more.

For scale, a 1 A load step unsupported by the converter for 10 µs removes
10 µC of charge. It would drop 44/22/11 µF by 0.227/0.455/0.909 V before
ESR. These are charge-balance examples, not predicted load steps or response
times for this regulator.

## Feed-forward network

For a capacitor across the top feedback resistor, the passive divider has
`fz = 1/(2π Rtop Cff)` and `fp = 1/(2π (Rtop || Rbottom) Cff)`.
Our 22 pF parts place the zero at 72.3/96.5/159.7 kHz for servo/5 V/logic.
This calculation does not include the converter's control law or establish
phase margin.

TI's 5 V example uses 220 kΩ/30 kΩ and 30 pF, giving a 24.1 kHz zero.
Our 75 kΩ/10 kΩ divider would need about 88 pF to preserve that top-resistor
time constant; 82 or 91 pF are candidates for review. For the logic divider,
30 pF is close to the 3.3 V reference example. There is no 6.6 V example
justifying a direct copy for the servo rail. We did not change C414/C424/C434:
copying a time constant without the actual effective output capacitance and
loop behavior would not validate a new value. Final loop/model work follows
the capacitor selection; bench transient tests follow assembly.

## Converter and inductor heat

We evaluated 486 cases per converter: 8/12/15 V input, low/nominal/high static
output voltage, 3.76/2.63 µH, assumed 400/600/800 kHz, 1/1.5/2 times typical
switch resistance, and assumed total switching overlap of 10/20/40 ns.
These frequency, resistance and overlap sweeps are sensitivity assumptions,
not manufacturer tolerance limits. The 144 logic cases with nonpositive
inductor-current valleys are excluded: the Eco-mode part needs a different
light-load model there. Remaining results do not bound discontinuous operation.

| Rail allocation | Largest modeled IC conduction + overlap loss | Required effective IC-to-air thermal resistance at assumed 40 °C ambient, before other losses | Largest external inductor copper loss at 25 °C |
| --- | ---: | ---: | ---: |
| Servo, 4 A | 2.204 W | At most 38.6 °C/W | 0.399 W |
| 5 V, 3.3 A | 1.568 W | At most 54.2 °C/W | 0.275 W |
| Logic, 0.8 A | 0.240 W | At most 354 °C/W | 0.020 W |

These are hypothetical demands on cooling, **not predicted dissipation or
temperatures**. Required resistance uses `(125 − 40)/loss`. IC loss omits
gate drive, output capacitance, dead time and control losses. Inductor loss
uses 23.4 mΩ, the +20% DCR corner at 25 °C, and excludes hot copper/core loss.
The largest valid-case inductor peaks are 5.768/4.913/1.598 A. This does not
qualify a fault: the IC's current-limit valley can reach the inductor's stated
saturation test current before ripple is added.

At nominal frequency, nominal output and typical cold switch resistance,
conduction-only maxima over the input sweep are 0.795/0.480/0.026 W. Thus
the cold conduction number alone can substantially understate the modeled
cooling demand. TI's effective 74 °C/W came from its 2 oz evaluation board;
our 1 oz outer copper, ground connections and nearby heat sources differ.
The JEDEC thermal figure is also not a board-specific prediction. See
[TI's thermal-metric guidance](https://www.ti.com/lit/an/spra953c/spra953c.pdf).

We should preserve heat-spreading copper and ground vias when resolving the
heatsink conflicts, then evaluate the finalized layout and intended duty.
The servo's 4 A allocation is not a claim of sustained 4 A operation. The
published servo stall endpoint is 3 A, and a realistic duty profile must be
kept separate from the full-allocation sensitivity cases.

## L298 and heatsink

[ST's 25 °C electrical table](https://www.st.com/resource/en/datasheet/l298.pdf)
gives maximum total bridge drops of 3.2 V at 1 A and 4.9 V at 2 A.
With two bridges conducting continuously, `P = Σ(I × Vdrop)` gives
6.4 W and 19.6 W respectively, before other losses. These are datasheet
test-point calculations, not measured motor currents or allowed operating
instructions; 2 A per bridge is an absolute maximum.

Using a chosen 125 °C design target, assumed 40 °C ambient, 3 °C/W
junction-to-case and an assumed 1 °C/W interface, the corresponding maximum
sink-to-air resistances would be 9.28 and 0.34 °C/W before additional losses.
The [6396BG manufacturer record](https://www.farnell.com/datasheets/1581373.pdf)
quotes 5.6 °C/W at a 75 °C rise in natural convection; it is not constant
across heat loads, orientations or obstructed airflow. Neither its acceptance
for review nor this arithmetic establishes sustained two-bridge operation
at the absolute maximum. Do not extrapolate the table to a 3.2 A motor stall.

The [mounting drawing](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Cooling-High-Power-Extruded-6390.pdf)
and electrical calculation are available now. The actual attachment, interface
and motor-fault policy still determine the useful final thermal model. A
detailed temperature simulation with guessed attachment would add false
precision; resolving those choices is the next useful step.

## Verification and remaining work

`python check_power_margins.py` regenerates the report after the upstream
CAD-derived checks. `python -m unittest test_power_margins.py` independently
integrates sampled switch/inductor waveforms, compares the feedback divider
with complex impedances and rejects invalid buck/DCM cases. All four tests
pass. Source hashes match the saved PCB and prerequisite reports.

Completed: the voltage-limit comparison, capacitor-retention targets,
feed-forward comparison, ripple/current and thermal sensitivity calculations.
Still open: supply/return refinement, encoder supply qualification, exact
capacitor data and final loop choice, final cooling layout, and the existing
battery/protection/mechanical decisions. These are not all measurement
dependencies. Physical voltage/ripple/temperature tests belong after assembly;
we do not request a new general measurement campaign for this review.
