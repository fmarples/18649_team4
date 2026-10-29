# Supply-path resistance screening

Current October 28 update: the saved PCB uses the revised capacitor banks,
separate 4.0 V encoder supply, one Pi 5 V contact and seven Pi ground contacts.
The new Pi positive-feed result is 4.9424 V at the 3 A planning allocation.
Current calculation JSON files carry the saved board hash; older numerical
discussion below is a dated review record. See [Power-margin-review.md](Power-margin-review.md)
and [Capacitor-bank-review.md](Capacitor-bank-review.md) for the active assessment.


## Current revision — October 27

The [mounting and encoder revision](Mounting-and-encoder-revision.md) supersedes
older socket, heatsink-placement and encoder-voltage statements below. All
eight supports now meet the 3 mm hole-edge rule; HS80 is installed; encoders
have a separate 4.0 V supply. Current JSON checks carry the active board hash.
Battery/protection, Pi voltage margin and exact capacitor data remain open.

## Earlier review record


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

The previous pass widened 474 logic segments and specified 0.1% R430/R431
feedback resistors. This pass widens 768 existing 3.3 V segments and 541
existing 5 V segments, including narrow supply necks. Clear space permits
up to 3 mm on logic and 4 mm on 5 V; crowded sections remain narrower.
These are segment counts, not separate nets or full-length power buses.
The nominal setpoints, component positions, pad geometry and signal routes
are unchanged. [Supply-copper-change.json](Supply-copper-change.json) records
each width change against the previous board hash.

| Same shared-current case | Previous feed drop | Current feed drop | Current source minus feed drop |
| --- | ---: | ---: | ---: |
| Worst CAN load (previous U21, now U25) | 0.143922 V | 0.094885 V | 3.167996 V |
| Encoder J82 | 0.143458 V | 0.093169 V | 3.169712 V |
| Pi J70 at 3 A | 0.158744 V | 0.149796 V | 4.864848 V |

The larger logic improvement comes from relieving narrow connecting
sections, not just widening already-wide trunks. We retained the old widths
near six front-ground patches after the first candidate split a ground
patch. The accepted board has zero unconnected items and zero DRC findings;
no new solid pad connection or relaxed clearance rule was needed. The CAN
reference sample check was rerun after filling the ground zones.

These values exclude ground return, contacts, heating and regulator
load/line/transient behavior. Full segments are counted and parallel paths
are not solved, so this is neither a measured voltage nor a guaranteed lower
bound. The earlier full-rail-per-branch screen remains available in
[Supply-path-check.json](Supply-path-check.json).

As a sensitivity example, approximately 60 °C copper and 20% narrower traces
give about 1.45 times nominal resistance. Multiplying the current worst CAN
feed drop by 1.45 and reserving an assumed 50 mV for return leaves about
3.075 V. The corresponding Pi result is about 4.747 V. These assumptions do
not bound thickness, via plating or shared-ground effects. The 20 µm via
plating assumption is not a guaranteed minimum; JLCPCB lists 18 µm average.

The [voltage-margin comparison](Power-margin-review.md#voltage-available-at-the-loads)
keeps the device limits separate. The encoder connector is still below its
recorded 3.3–5 V range, and the source low corner itself is only 3.263 V.
Wider copper cannot resolve that specification question. The Pi has only
3.3 mV left before the upper tolerance of its low-voltage detector, before
other losses. That detector is not a minimum operating specification.
Complete the encoder supply decision and full Pi/logic return/loss budget
before release; these are design findings, not measured failures.

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
reroute stays on B.Cu. Those earlier via moves left Pi feed resistance unchanged; the later width
refinement above changes it. Ordinary DRC does not check solder wicking.

## Checker validation

A temporary synthetic board checks that touching tracks connect, separated
tracks do not, and coincident tracks on opposite layers stay separate without
a via. A 10 mm × 1 mm × 0.035 mm trace produces 4.914 milliohms as expected.
The saved-board geometry graph must agree with KiCad's zone-excluding
connectivity for every reported target. These checks validate the calculation
mechanism, not the assumed material properties or hardware behavior.

## Bulk ground-return follow-up — October 27

[Ground-plane-review.md](Ground-plane-review.md) now screens the saved In1
fill under the same logic/5 V load allocation plus two whole-system current
scenarios. It compares each load's ground with the lower feedback resistor's
ground. The output-loop-only fine-grid case subtracts another 5.68 mV at
J70, giving 4.8592 V before contact and local-return losses. Other loads can
move the feedback reference in either direction; favorable offsets are not
guaranteed headroom. The model leaves the source-minus-feed calculation above
intact and does not qualify the complete supply voltage. Local connections,
contacts and regulator load/line behavior still belong in that final budget.
