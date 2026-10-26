# Supply-path resistance screening

26 October 2026. We calculated resistance from the saved trace geometry. This
is an initial sizing check, not a powered test or fabrication release.
`check_supply_paths.py` and [Supply-path-check.json](Supply-path-check.json)
record the method, assumptions and board hash.

## Calculation

The script joins conductors only where their copper shapes overlap on a common
layer. It checks target connectivity against KiCad's graph with zones excluded,
then finds a low-resistance path from the output inductor to each load. Each
traversed track contributes `R = resistivity × length / (width × thickness)`.
Whole track lengths are counted even when a junction is partway along a track;
parallel routes are not solved as a resistor network.

We use copper resistivity 1.72e-8 ohm-metres at approximately 20 °C, 0.035 mm
outer copper and 0.0152 mm inner copper from our [reference stack](Layer-stack.md).
Via resistance assumes 0.020 mm plating and a full 1.6 mm barrel. Actual plating
has not been established. Pad spreading, contacts, ground-return resistance,
heating and regulator transient/load/line behavior are omitted.

For screening, we apply the entire rail allocation to each path separately:
0.8 A on 3.3 V and 3.3 A on 5 V. This overstates the current of individual
small-load branches. It is not an estimate of their normal operating current,
and the omitted losses mean it is not a guaranteed worst-case load voltage.

## Results and remaining design work

| Path | Calculated conductor resistance | Screening drop |
| --- | ---: | ---: |
| L2.2 to Pi J70.2 | 0.0564 ohm | 0.186 V at 3.3 A |
| L2.2 to Pi J70.4 | 0.0580 ohm | 0.191 V at 3.3 A |
| L3.2 to checked MCU/CAN supply pads | 0.0642–0.3504 ohm | 0.0513–0.2803 V at 0.8 A |

For example, subtracting the J70.4 path drop from the regulator's 5.014644 V
static component-tolerance corner gives 4.823 V before the omitted losses.
We have not established adequate operating margin from this calculation alone.

Before fabrication, assign currents to the shared trunks and individual loads,
widen or parallel the demanding paths, and review vias and return copper.
The Pi path currently includes seven through vias in the selected path; their
current sharing and temperature rise need attention. A native DRC pass does
not establish current capacity. Motor and servo routes need the same current,
voltage-drop and return-path review; this script currently screens only 3.3 V
and 5 V.

We moved the five transitions at R1.2, U2.3, U3.4, Q1.3 and C430.1 outside
their SMD solder lands and used two 0.70/0.30 mm vias at each site. The supply
paths remain connected. Parallel vias still require current-sharing and
temperature review; a DRC pass does not establish their rating.

We also moved two transition sites at D804.1 and one at D802.2 outside
their solder lands, with paired vias at each site. D807.1 remains unresolved.
The sense-branch via at U1.4 and other small-signal/supply sites also need
assembly review. Move
these transitions or explicitly qualify the fabrication treatment before
release. Ordinary DRC does not check solder wicking.

## Checker validation

A temporary synthetic board checks that touching tracks connect, separated
tracks do not, and coincident tracks on opposite layers stay separate without
a via. A 10 mm × 1 mm × 0.035 mm trace produces 4.914 milliohms as expected.
The saved-board geometry graph must agree with KiCad's zone-excluding
connectivity for every reported target. These checks validate the calculation
mechanism, not the assumed material properties or hardware behavior.
