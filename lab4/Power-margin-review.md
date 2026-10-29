# Power margins, capacitors and thermal review

Updated 28 October 2026. We recalculated these margins after moving the 5 V regulator
closer to the Pi and rerouting its connections. The buck setpoints are unchanged;
the separate encoder LDO remains in place. The
calculations identify limits of the present design; they do not
qualify it for fabrication. [Power-margin-check.json](Power-margin-check.json)
records the source hashes, assumptions and numerical results. The selected 3S LiPo reaches 12.6 V when full. We retain the existing
8–15 V design screen; it is not the battery discharge cutoff.

## Current voltage results

The mounting/encoder revision adds a separate 4.0 V supply. Its conservative
static connector screen is 3.792/3.794 V, rather than the earlier 3.17 V
from the logic rail. The LVC14A and pull-ups remain at 3.3 V. See
[Mounting-and-encoder-revision.md](Mounting-and-encoder-revision.md).

The revised positive-feed path to Pi pin 4 is 23.000 mΩ, down from
32.668 mΩ. A wider alternate route avoids the inductor core gap; component
placement and schematic nets are unchanged. The shared-load calculation now
gives J70 **4.9424 V** at the assumed 3 A Pi allocation, versus 4.9116 V
previously: a 30.8 mV improvement. The logic result at U25 remains 3.1677 V.
This is before contact, local return, hot-copper and dynamic losses. The
4.8615 V upper undervoltage-warning corner is not a guaranteed operating limit.

The shortened socket supplies 5 V through **one contact (pin 4)** and has
seven ground contacts. An illustrative 10/20/30 mΩ resistance per contact,
with equal ground-current sharing, loses 34.3/68.6/102.9 mV at 3 A:
I × (Rc + Rc/7). These are sensitivity assumptions, not guaranteed contact
ratings. The complete voltage budget therefore still needs review; a cleaner
route alone does not guarantee full-load Pi operation. See
[Samtec's connector specification](https://suddendocs.samtec.com/catalog_english/esq_th.pdf).

These predecessor-tree calculations count whole items, omit parallel copper
and pad spreading, and omit contact/local return/heating/dynamic losses.
They are neither measured voltage nor guaranteed worst-case bounds.
[Load-allocation-check.json](Load-allocation-check.json),
[Ground-plane-check.json](Ground-plane-check.json) and
[Power-margin-check.json](Power-margin-check.json) contain refreshed results.
The ground model now returns the 40 mA encoder load at J82/J83; only U82's
quiescent allocation returns at U82. Final Pi/load/thermal decisions remain
open. A larger power-routing redesign should use the confirmed load and
battery envelope. No generic efficiency or contact-resistance assumption
has been promoted to a guaranteed specification.

## Revised capacitors and feed-forward network

We replaced the earlier single 22 µF input / two 0805 output arrangement.
All nineteen bank parts now use Murata GRM32ER61E226KE15L, 22 µF/25 V X5R
1210, ±10%. Each input has three parts plus 100 nF. Servo/Pi/logic outputs
have four/three/three parts: 88/66/66 µF nominal. C414/C424/C434 now use
68/91/30 pF C0G feed-forward parts. C700 remains the separate 0805 Pi bypass.

[Capacitor-bank-review.md](Capacitor-bank-review.md) gives exact sources,
bias readings, selection rationale, ripple/ESR examples and limitations.
The combined planning screen applies conservative readings of the typical
bias plot, −10% tolerance, −15% temperature and an assumed −20% aging factor.
It gives input capacitance 14.14 µF at 12.6 V and 12.12 µF at 15 V. The
servo/Pi/logic outputs give 32.31/30.29/32.31 µF, with calculated LC poles
17.26/17.83/17.26 kHz at the 2.63 µH rolloff sensitivity. These exceed the
stated >10 µF input and 24.08 µF output planning targets; they are not
manufacturer-guaranteed combined minima or measurements.

The earlier typical curves showed why the old design needed revision:
one input capacitor fell to about 8.8 µF at 12.6 V before tolerances, while
the small 0805 outputs lost roughly 40/62/70% at 3.3/5.1/6.6 V.
The [input-family curve](https://static.chipdip.ru/lib/973/DOC031973461.pdf)
and [old output-family curve](https://datasheet.octopart.com/GRM219R61C226ME15L-Murata-datasheet-140706706.pdf)
are manufacturer-authored typical characteristic sheets, not production limits.
The unselected Wurth comparison in Capacitor-candidate-check.json remains a
historical alternative study; it does not describe the current BOM.

The new feed-forward values follow TI's documented examples while adapting
the passive-divider time constant: servo/Pi zeros are about 23.4/23.3 kHz,
near the 24.1 kHz 5 V example; the logic value follows its 3.3 V example.
All selected values fall within the 10–100 pF guidance. We have not simulated
the encrypted PSpice model or established full-loop phase margin. Added bulk
branches and vias have inductance, so arithmetic capacitance alone does not
prove switching-frequency behavior. Startup, ripple, representative load
changes and component temperatures remain prototype validation tests.

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

We preserved local heat-spreading copper and ground vias in the placement
changes; the finalized layout and intended duty still need evaluation.
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

The [mounting review](Heatsink-mounting-review.md) now specifies a screw-clamped,
greased tab interface and two soldered PCB anchors from manufacturer drawings.
The implemented placement, airflow and motor-fault/duty policy determine
the final cooling assessment. The assumed 1 °C/W interface above is still a
screening value, not a measured or guaranteed resistance for this assembly.

## Verification and remaining work

`python check_power_margins.py` regenerates the report after the upstream
CAD-derived checks. `python -m unittest test_power_margins.py` independently
integrates sampled switch/inductor waveforms, compares the feedback divider
with complex impedances and rejects invalid buck/DCM cases. All four tests
pass. Source hashes match the saved PCB and prerequisite reports.

Completed: the voltage-limit comparison, revised capacitor-bank selection and
retention screen, feed-forward selection, ripple/current and thermal calculations.
Still open: the full supply/return budget and complete loop/layout review,
cooling qualification, motor/fuse protection decisions and final
assembly process. Encoder supply calculations and heatsink placement are
complete for their stated assumptions. These are not all measurement
dependencies. Physical voltage/ripple/temperature tests belong after assembly;
we do not request a new general measurement campaign for this review.
