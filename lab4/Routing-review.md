# Power, MCU, CAN and signal routing

26 October 2026. The saved **four-layer** PCB has **13,721 track segments,
829 through vias and six filled ground zones**. Missing connections fell from
**128 to 59** across today's revisions. **Nine MCU signal nets and board-wide
power paths are still incomplete.** All 284 electrical footprints, eight supports,
positions, values and pad nets are unchanged. This is not a fabrication release.

## Latest MCU, supply and ground routing

We connected six further MCU nets: front console TX, task probe, front-left
LED and degraded-B LED; rear right-encoder A and error LED. Nearby blocking
signals were rerouted and rechecked. Footprint positions and pad nets stayed
unchanged; signal tracks remain 0.20 mm with 0.70/0.30 mm through vias.

Nine new 3.3 V joins connect the main MCU/CAN groups to the logic regulator.
R804.1 and R807.1 are still disconnected, leaving three separate 3.3 V pad
groups. Seven local 5 V joins connect bypass, sensor, header and pull-up
branches; they do not complete the regulator-to-load distribution. Supply
width, voltage drop and load-current capability still need review.

We added twenty ground stitching vias near CAN layer transitions and changed
J605.1's thermal-spoke angle from 90 to 0 degrees and set explicit 0.20 mm spoke
width/gap overrides. Native DRC confirms no starved thermals or disconnected GND items.
No additional solid-connected pad or global rule relaxation was needed.

[Layer-stack.md](Layer-stack.md) records the JLC04161H-7628 reference stack.
[Return-path-review.md](Return-path-review.md) records the initial ground,
feedback and sense-path checks and the remaining geometry review. These
checks establish specific connections, not signal integrity or current ratings.

The last checked two-layer board is preserved at
[lab4-two-layer-archive](https://github.com/fmarples/18649_team4/tree/lab4-two-layer-archive/lab4).
Continue design work on the four-layer `lab4` branch.

## Earlier October 26 four-layer routing

Staff [allow four layers](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793033728122419).
We added a ground plane on In1.Cu and moved eligible thin signal routes from
B.Cu to In2.Cu. That checkpoint retained 4,509 of those moved segments. Wider
power/ground tracks and nets with bottom SMD pads stayed on the outer layers.
Mounting and antenna rule areas now apply to both inner layers. The six ground
zones are filled; native DRC reports no disconnected GND items. This does not
establish low-noise or sufficient high-current return paths everywhere.

We added twelve MCU nets after the earlier four-net checkpoint: front right LED,
RX-A marker, status LED, steering-task marker, degraded-A LED and TX-B marker;
rear direction-A marker, IN2, task probe, PID marker, status LED and overload marker.
To make room we rerouted front MOSI/servo PWM and rear INT-A/IN4. Their 330 old
copper objects were replaced. All 11,804 other retained old copper objects keep
their geometry; only the selected B.Cu-to-In2.Cu layer changes differ.

We added 0.50 mm R201.1-to-R805.1 and 0.80 mm R806.1-to-C803.1 supply joins.
That earlier checkpoint left twelve separate 3.3 V pad groups; the latest
joins above reduced this to three.
Widths are design choices, not measured current/temperature ratings.

U81.13 initially had only one usable ground thermal spoke. We changed its angle
to 45 degrees and its spoke width/gap to 0.20/0.20 mm, then added a seven-segment
0.20 mm ground connection to U81.11. Native DRC checks the resulting island
continuity. It remains a thermal-relief pad; no additional solid pad or global
rule relaxation was used. No starved thermal or dangling copper findings remain.

The nominal board thickness remains 1.6 mm. The physical reference stack and
copper weights are now documented in Layer-stack.md. We still need to review
CAN geometry and return paths and export all four copper Gerbers for fabrication. No controlled
impedance is claimed. The four SVG layer previews are inspection aids.

## Earlier October 26 two-layer checkpoint

We connected rear IN3, front TX-A marker, rear relay-TX marker and rear
steering-task marker, rerouting rear IN1, front error LED, rear left-enable PWM
and rear LEFT_ADC. We also added 25 ground joins. That checked checkpoint had
101 missing connections and 239 passing connection checks. Its source and
validation remain in Git history; the four-layer board supersedes it.

## Connections completed in this revision

For each MCP2515, we connected its crystal and load capacitors, local bypass,
reset network, inactive RTS inputs and chip-select pull-up. TXD/RXD now reach
the transceiver and test header. The transceiver has a local bypass connection,
ground connections and CAN H/L connections to its isolation header. Each node's
backbone-side test pins and, where fitted, termination jumper/resistor are
connected locally. Both CAN A/B backbones now connect the rear, cockpit and
front nodes. The main runs are front-layer pairs with 0.20 mm tracks and
0.60 mm center spacing (0.40 mm copper gap). Bus A goes around the Pi support
and header; Bus B follows the right edge. Branch fanouts now use the outer
layers and In2.Cu.
These dimensions do not establish a controlled-impedance rating; pair/return
geometry and signal behavior still need final review.

We moved 48 CAN support footprints to shorten the critical paths. Each crystal
is beside its controller's oscillator pins. All 12 oscillator nets use only
front-layer copper, without vias; total branch copper is approximately 5.62 mm
for OSC2 and 9.65 mm for OSC1, including the capacitor connection. The transceiver
bypass sits in the space between the controller and transceiver. Short local
connections reduce loop area and parasitic inductance. Crystal load-capacitor
values are unchanged; startup and frequency have not been tested.

For both STM32s, we connected the individual VDD/VBAT bypass capacitors, local
bulk capacitor, VCAP capacitor and filtered VDDA supply. Reset, BOOT0 and
self-test networks are routed, including both physical pads of each switch
contact. Ground vias connect these local grounds to the bottom reference plane.
The latest supply joins connect these MCU/CAN groups to the 3.3 V regulator;
two pull-ups and the final trunk width/voltage-drop review remain open.

Schematic values, pin assignments, package identities, mounting holes and
regulator copper are unchanged. No battery or heatsink decision was needed for
these local routes. The new local signal tracks are 0.20 mm wide; vias are
0.70 mm diameter with 0.30 mm drills. The general 0.20 mm clearance and existing
fabrication rules are unchanged.

## Host interfaces

Both STM32s and the Pi now connect to their two MCP2515 controllers. We kept
the Lab 3 pin assignments: shared SCK/MISO/MOSI and independent CS/INT per
controller. The six CS pull-ups remain on their corresponding chip-select
nets. Short pin escapes lead to through vias; longer connections use the signal
copper layers. The Pi controller escapes extend into open space before
joining the header and second controller.

This pass changes only copper. Component values, footprints, positions,
schematic pin nets were preserved in that host-interface pass.
Host signal width is 0.20 mm and new vias use 0.70 mm diameter / 0.30 mm drills.
We added 0.20–0.30 mm local ground bridges where bottom-layer signals divided
the reference copper, then rerouted affected host signals around those bridges.
J604.1 uses a 45-degree thermal-spoke angle, and both J604 ground pads have
explicit copper connections to the ground network. The minimum-spoke rule
is unchanged. Native DRC checks the resulting ground islands; the grouped-zone
connectivity graph alone does not establish their continuity.
These routes still need signal-return/ground-plane review with the rest of
the board; no SPI waveform, maximum clock speed or hardware operation has
been validated.

## Sensing, control and diagnostic signals

We connected 76 additional signal nets. These include all three current-sense
output/filter/divider/ADC chains; all four encoder input filters and three of
the four conditioned encoder outputs; servo PWM and its connector-side series
resistor; both motor-enable PWM nets and IN1/IN4; the lamp transistor/resistor
connections; the Pi indicators, self-test and timing probes; and portions of
the MCU debug, indicator and timing-header wiring. The fourth conditioned encoder
output and IN2 are now routed. Several MCU diagnostic/indicator pins remain open;
the exact nine incomplete signal-net names are in `Routing-check.json`.

Signal tracks are 0.20 mm wide with 0.70/0.30 mm through vias. The switching
regulator cells and mounting/antenna reservations are preserved. New routes
do not change the schematic or pin map. We connected both physical ground
contacts of SW70 and added local ground bridges where signal tracks divided
the plane. The latest ground-connection choices are recorded below.

## Supply branches, servo sensing and ground reference

Rear UART TX/RX now connect U60 pins 44/45 to J602 pins 1/2. Eleven checked
3.3 V branch joins use mostly 0.80 mm copper, with two 0.50 mm connections.
These earlier joins connected local groups. The latest pass connected the main
MCU/CAN groups to the regulator; other power rails and two 3.3 V pull-ups remain open.

R1's two shunt terminals now have separate 0.20 mm sense connections to U1
IN+ and IN-. They leave the inner terminal edges; the regulator power feed
enters the opposite side of the source terminal. L1.2 reaches R1.1 through a
2.0 mm main track with a short 0.80 mm pad approach. The load-side path from
R1.2 to J90 is still open. These connections require a final noise/loop and
current/temperature review; connectivity alone does not qualify the sensing
accuracy or the load-current rating.

The new front ground plane excludes the three existing regulator cells, whose
local pours remain. Forty-one 0.80/0.40 mm stitching vias join front and back
ground copper. C5.2 and C8.2 also have explicit 0.30 mm ground traces to the
corresponding sensors. Those two pads use trace connections instead of
direct zone attachment. A filled zone can contain separate islands: native
unconnected-item checks remain necessary, and final signal-return review is open.
The copper previews still show large breaks in the front reference around the
MCU escapes and through the middle of the board. The added plane does not
provide a continuous reference beneath every route; check layer transitions
and return detours when revising the remaining fanout.

## Thermal relief decisions

A thermal relief joins a pad to a copper plane through narrow spokes, reducing
the heat drawn away during soldering. The earlier five solid connections were
a response to the available copper geometry and minimum-spoke rule, not a
fundamental inability to route these pads. Moving nearby copper or adjusting
spoke angle, width and gap can restore a relief.

- J501.3 and J601.3 now use thermal reliefs again: 0-degree angle, 0.30 mm
  spokes and 0.25 mm gap.
- J601.6, J704.2 and J70.20 still use solid ground connections. J70.14 also
  uses a solid connection because the new front plane left only one usable
  thermal spoke. These four through-hole pads will draw more soldering heat.
- U60.47 uses 45-degree, 0.20 mm spokes with a 0.20 mm gap. C5.2/C8.2 have
  the explicit ground traces described above.

The global two-spoke minimum, 0.20 mm clearance and fabrication rules are
unchanged. We did not suppress a thermal warning or infer a current rating
from a DRC pass. See the [KiCad zone documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html).

The remaining MCU signals need a revised local fanout, potentially including
nearby bypass placement. These are CAD tasks, not measurement dependencies.
Trial routes that broke existing supply connections or failed native DRC were
excluded from the saved revision.

## Previously completed regulator connections

Each TPS564252 connects to its local input capacitors and enable divider,
inductor, output capacitors, feedback divider and test header. Feedback,
enable and power-good nodes are connected locally. A separate output-sense
trace runs from the output capacitor to the divider, away from SW.

The initial power paths use 0.6–1.6 mm tracks after short 0.2 mm pad escapes.
Power-ground vias use 0.8 mm diameter / 0.4 mm drills. These dimensions are
design choices, not verified current or temperature ratings. Board-wide feeds,
two 3.3 V power-good pull-ups, Kelvin-return and switching-loop review,
effective capacitance and thermal/current qualification remain open.

## Verification

- `check_routing.py` walks KiCad's physical copper-connectivity graph. All
  **275 targeted connection checks** pass: 21 regulator, 76 local CAN, 14 MCU,
  four backbone nets, 21 host-interface nets, 76 additional signal nets, eleven
  supply branches, two shunt inputs, one servo power-feed connection, two UART
  nets, two filter-ground connections, sixteen more MCU signal nets, two further supply joins and five
  explicit ground-bridge checks, plus six latest MCU nets, nine 3.3 V joins and
  seven local 5 V branches. The five bridge checks exclude zone objects, which can
  otherwise represent multiple disconnected islands. Each backbone net reaches all eight required
  pads across the three zones, with termination on the bus side of isolation.
  It also checks the duplicated physical switch contacts and front-only clock
  copper. Removing U10's OSC1 copper in a temporary copy correctly causes a
  failure even though the pads retain their schematic net names. A second
  temporary fault test removes front-host SCK copper and correctly fails
  the new U50 host-SCK check. Removing LEFT_ADC copper from another temporary
  copy correctly fails its new signal-endpoint check despite unchanged pad nets.
  The duplicate switch-pad check now compares physical pad identities; it
  detected SW70's separated ground contacts before they were connected.
  Removing the SERVO_VPLUS sense copper in a temporary copy correctly fails
  the new Kelvin IN- check while the schematic pad nets remain unchanged.
  A new temporary fault board removes rear IN3 and ground copper; the IN3
  check and all five zone-excluding bridge checks fail as intended.
- ERC on the unchanged schematic, fresh ordinary DRC and schematic parity
  have zero findings. The remaining
  59 unconnected items are reported as fabrication blockers in
  [Fabrication-check.json](Fabrication-check.json), not suppressed.
  Whole-board routing is unfinished; ground/return continuity remains a release check.
- All 284 electrical footprints and their pad nets match the schematic.
  Placement coordinates and previews match the saved board; all original
  regulator track/via objects and all non-CAN footprint positions are preserved.
- [Routing-check.json](Routing-check.json) records connection groups, clock
  lengths, widths, via sizes and the source hash. Native copper plots are
  [front](Routing-front.svg), [back](Routing-back.svg),
  [inner ground](Routing-inner-ground.svg) and [inner signals](Routing-inner-signals.svg).

KiCad 10 caps its DRC unconnected list at 499 entries; our audit also records
the full connectivity count. Both now report 59. The earlier regulator-only
revision had 648 missing connections, although its DRC list stopped at 499.
See the [KiCad DRC engine source](https://github.com/KiCad/kicad-source-mirror/blob/10.0/pcbnew/drc/drc_engine.cpp).

## Remaining routing

Board-wide power/load-current paths and nine MCU-related signal nets still need
routing. The two Kelvin input connections exist; their final geometry review
is still required. Review CAN pair geometry, continuous reference copper, return paths
and power-loop/thermal behavior before layout freeze. These digital routes
can continue without new lab measurements. Battery/input-power, motor-fault
protection and heatsink choices affect their specific areas.

Design references: [MCP2515 datasheet](https://www.microchip.com/content/dam/mchp/documents/APID/ProductDocuments/DataSheets/MCP2515-Family-Data-Sheet-DS20001801K.pdf),
[SN65HVD23x layout guidance](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf),
[INA180 layout guidance](https://www.ti.com/lit/ds/symlink/ina180.pdf),
and [TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf).
See [Power-stage-review.md](Power-stage-review.md) for regulator calculations.
No new-board electrical, oscillator or thermal measurement is claimed.
