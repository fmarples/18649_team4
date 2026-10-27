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
| L2.2 to Pi J70.2 | 0.0495 ohm | 0.164 V at 3.3 A |
| L2.2 to Pi J70.4 | 0.0511 ohm | 0.169 V at 3.3 A |
| L3.2 to checked MCU/CAN supply pads | 0.0671–0.3855 ohm | 0.0537–0.3084 V at 0.8 A |

For example, subtracting the J70.4 path drop from the regulator's 5.014644 V
static component-tolerance corner gives 4.846 V before the omitted losses.
We have not established adequate operating margin from this calculation alone.

We widened 107 existing 5 V segments where clearance permitted, added a
parallel 0.70/0.30 mm via at six Pi supply transitions and enlarged the seventh
transition to 0.80/0.40 mm. The selected single path still counts seven vias;
the calculation does not credit the added parallel paths. The larger Pi-path
screening drop decreased from 0.191 V to 0.169 V. We preserved the narrower
section beside the Pi antenna reservation.

The CAN-reference repair replaces a 10.833 mm 3.3 V feed with a 47.303 mm
route and four added vias. Its minimum width is 0.50 mm, with clear sections
widened as far as 1.50 mm. Moving solder-pad vias also adds local copper.
Together these changes increase the largest 3.3 V path screening drop from
0.2803 V to 0.3084 V under the same full-rail stress. Preserving the CAN
reference does not remove the need to size this longer supply path. The full
0.8 A stress on each individual MCU/CAN branch is not its expected load.

Before fabrication, assign currents to shared trunks and individual loads,
include their ground-return paths, and check voltage and thermal margins.
The 3.3 A stress applied to U80/U2/U3 in the JSON is not their operating current:
the rail allocation includes the Pi. A native DRC pass does not establish
current capacity or sufficient Pi input voltage.

## Motor and servo copper

We widened 333 existing motor/servo segments while preserving shunt sense
branches and the U80.1 thermal passages. Sections beside mounting-hole and
keep-out boundaries retain their original widths. No footprint or pad changed.

| Copper path | Calculated resistance | Screening drop |
| --- | ---: | ---: |
| Servo L1.2 to R1.1 | 0.00373 ohm | 0.0149 V at 4 A |
| Servo R1.2 to J90.2 | 0.02480 ohm | 0.0992 V at 4 A |
| Left motor: U80 output to sensor, sensor to connector, connector to U80 return | 0.02635 ohm total | 0.0843 V at 3.2 A |
| Right motor: corresponding three sections | 0.01887 ohm total | 0.0604 V at 3.2 A |

Servo copper contributes about 0.114 V and 0.457 W at the provisional 4 A
allocation, down from 0.123 V and 0.491 W. The 0.010 ohm shunt adds another
0.040 V and 0.160 W; it is not included in the copper figures. These values
still omit the servo ground return and connector/cable losses.

Motor totals add one path through each series section, not both parallel
ACS712 input pins. They exclude the sensor's internal conductor, L298 bridge,
external motor wiring and battery supply/ground paths. The 3.2 A value is a
catalog stall stress case, **not an allowable L298 operating current**.
Current limiting and thermal behavior remain unresolved.

We moved the five transitions at R1.2, U2.3, U3.4, Q1.3 and C430.1 outside
their SMD solder lands and used two 0.70/0.30 mm vias at each site. The supply
paths remain connected. Parallel vias still require current-sharing and
temperature review; a DRC pass does not establish their rating.

We also moved two transition sites at D804.1 and one at D802.2 outside
their solder lands, with paired vias at each site. The latest pass also moves
D807.1 and U1.4 outside their lands; D807 uses a 0.80/0.40 mm via and 0.80 mm
bridges. Across the latest revision, 70 existing vias were relocated and
nominal drill/land intersections fell from 98 to 28. See
[Solder-via-review.md](Solder-via-review.md) for the remaining sites and
mask/paste limitations. Ordinary DRC does not check solder wicking.

## Checker validation

A temporary synthetic board checks that touching tracks connect, separated
tracks do not, and coincident tracks on opposite layers stay separate without
a via. A 10 mm × 1 mm × 0.035 mm trace produces 4.914 milliohms as expected.
The saved-board geometry graph must agree with KiCad's zone-excluding
connectivity for every reported target. These checks validate the calculation
mechanism, not the assumed material properties or hardware behavior.
