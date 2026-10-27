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

## Shared-trunk load allocation and refinement

27 October update: [check_load_allocation.py](check_load_allocation.py) now
sums downstream currents on a least-resistance routing tree. This includes
the longer 3.3 V feed. Whole segments are counted, and parallel copper is not
solved as a network. Each MCU's entire current is assigned to its worst
supply pin; the Pi's allocation is put on the worse of pins 2/4 even though
both are wired. These choices are screening assumptions, not observed loads.

| Allocation | Stated case | Total |
| --- | --- | ---: |
| 3.3 V | Two MCUs at 70 mA; six MCP2515s at 10 mA; six transceivers at 77 mA; two encoders at 20 mA; other IC/pull-up allowances | 0.716719 A |
| 5 V | Pi at 3 A; L298 logic at 40 mA; two ACS712s at 15 mA; four lamp resistor bounds and feedback divider | 3.165525 A |

The MCU allocation includes GPIO/indicator allowance. The encoder current
is provisional. For each transceiver we allocate 17 mA no-load plus
3.6 V / 60 ohms = 60 mA drive current; allocating all six at once overstates
normal bus operation. The 0.8 A and 3.3 A rail budgets remain unchanged.
See the per-load assumptions in [Load-allocation-check.json](Load-allocation-check.json).

We widened 474 retained 3.3 V segments where clearance allowed, as far as
2 mm, and specified 0.1% R430/R431 feedback resistors. Their nominal values
and 3.318 V setpoint are unchanged. The static source low corner increases
from 3.215216 V to 3.262881 V. The largest shared-tree drop falls from about
0.1626 V to 0.1439 V. Together these changes raise the lowest calculated
load voltage in this case from about 3.053 V to **3.119 V**.

The Pi's calculated shared-tree drop is about 0.159 V at its 3 A allocation,
giving about **4.856 V** from the 5.014644 V static source low corner. The
largest 5 V drop is 0.1647 V on a lamp branch. These values exclude ground
return, cable/contact loss, heating and regulator dynamic behavior. They do
not establish guaranteed device voltage. The earlier full-rail-per-branch
screen remains available in [Supply-path-check.json](Supply-path-check.json).

Copper resistance increases with temperature. As a sensitivity example,
60 °C copper is about 1.16 times its 20 °C resistance; a 20% narrower trace
has 1.25 times its nominal resistance. Combined, these give about 1.45 times
trace loss, before thickness/via/ground uncertainty. Do not spend the full
remaining voltage margin on one omitted effect. Applying 1.45 to the entire
0.143922 V path drop and reserving an assumed 50 mV for the return leaves
only about 3.004 V. This deliberately simple sensitivity case is not a
verified bound: it shows that small additional losses could consume the
remaining margin. The ground plane must be
included in the final DC/thermal model or engineering margin assessment.
The 20 µm via-plating assumption is also not a guaranteed minimum; JLCPCB's
capability page lists 18 µm average plating.

The later [voltage-margin comparison](Power-margin-review.md#voltage-available-at-the-loads)
checks the loads against different limits. The encoder connector's 3.119 V
screen is below its recorded 3.3–5 V supply range, whose endpoint tolerance
is unknown. The regulator's 3.263 V low corner itself is below 3.3 V, so copper
widening alone cannot close that question. The Pi screen also leaves no
allowance against the upper tolerance of its low-voltage warning detector;
that threshold is not an operating-voltage specification. Resolve the
encoder supply and refine feed/return geometry before release. These are
newly documented design limitations, not measured failures.

A synthetic Y network independently checks shared-current arithmetic:
a 10 mm common trunk and two 10 mm branches, all 1 mm wide and 35 µm thick,
with 0.1/0.2 A loads produce 1.966/2.457 mV drops. The checker matches these
analytic values. This validates the mechanism, not the real load assumptions.

Sources: [STM32F401](https://www.st.com/resource/en/datasheet/stm32f401re.pdf),
[MCP2515](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2515-Family-Data-Sheet-DS20001801K.pdf),
[SN65HVD231](https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf),
and [JLCPCB capabilities](https://jlcpcb.com/capabilities/Capabilities).

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
their solder lands, with paired vias at each site. A preceding pass also moved
D807.1 and U1.4 outside their lands; D807 uses a 0.80/0.40 mm via and 0.80 mm
bridges. Before this revision's additional 32 clearance moves, we relocated 97 existing vias and
removed one redundant ground via. Nominal drill/land intersections fell
from 98 to zero. See
[Solder-via-review.md](Solder-via-review.md) for the remaining mask/paste
limitations. That preceding group of 19 moves added no supply-net vias; the 1.50 mm VBAT
reroute stays on B.Cu. Pi feed resistance is unchanged. Ordinary DRC does not check solder wicking.

## Checker validation

A temporary synthetic board checks that touching tracks connect, separated
tracks do not, and coincident tracks on opposite layers stay separate without
a via. A 10 mm × 1 mm × 0.035 mm trace produces 4.914 milliohms as expected.
The saved-board geometry graph must agree with KiCad's zone-excluding
connectivity for every reported target. These checks validate the calculation
mechanism, not the assumed material properties or hardware behavior.
