# Power, MCU, CAN and signal routing

26 October 2026. Every required PCB connection is now routed. The saved
**four-layer** board has **15,679 track segments, 960 through vias
and six filled ground zones**. Native DRC, ERC and schematic parity report
zero findings, and all **306** targeted connection checks pass. Both native
DRC and the full connectivity count report **zero missing connections**.
Power/current sizing, switching-loop and CAN return geometry, and the open
battery/protection/mechanical decisions still require review. This is not a
fabrication release or a powered test.

## CAN reference repair and solder-pad via relocation

We rerouted nearby 3.3 V and F_MOSI copper to restore bottom-layer ground
beneath the affected inner-layer CAN-A segments. The CAN backbone tracks and
vias are unchanged. The reference scan now finds zero gaps on all four CAN
nets at its sampled locations, excluding each signal's own through-hole
clearances. This is a local geometric improvement, not signal-integrity
qualification; layer detours and node/test/termination branches still need review.

The new 3.3 V feed is 47.303 mm long instead of 10.833 mm and uses four added
0.70/0.30 mm vias. Its narrowest section is 0.50 mm; clear sections are wider.
This preserves the nearby CAN reference at the cost of a longer supply path.
The updated [supply screening](Supply-path-review.md) records the increased
resistance so the next current-allocation review includes that tradeoff.

We inventoried nominal via-drill intersections with SMD solder lands and moved
70 existing vias outside those lands, including D807.1 and U1.4. The count fell
from 98 to 28; [Solder-via-review.md](Solder-via-review.md) identifies the
remaining work. D807's relocated via is 0.80/0.40 mm with 0.80 mm bridges.
One added ground stitch near CAN_B_L preserves a nearby return transition
after the ground-via moves. All recorded CAN signal transitions are within
3 mm of a ground transition, our review target rather than a device limit.

Footprint positions, pad geometry/nets, zone connection settings and design
rules are unchanged from revision 6164a13. In1 remains ground only. Fresh
ERC, DRC and schematic parity have zero findings; all 306 targeted checks
pass and the full connectivity count is zero. Explicit feedback-ground and
shunt-sense paths still pass with zones excluded. No hardware tests are claimed.

The sections below record earlier checkpoints. Their then-pending items are
superseded by the current status above and the linked engineering reviews.

## Earlier power-width refinement and CAN geometry audit

We widened 107 existing 5 V segments and 333 motor/servo segments where
clearance permitted. We added six parallel 0.70/0.30 mm vias along the Pi feed,
with short bridges on both outer layers, and enlarged the seventh transition
to 0.80/0.40 mm. Narrower sections beside mounting holes, the Pi antenna
reservation and the U80.1 thermal passages retain their previous widths.
Footprints, pad nets, thermal settings and design rules are unchanged from
revision fa1fa24. In1.Cu remains ground only.

The larger calculated Pi feed drop decreased from 0.191 V to 0.169 V at the
3.3 A rail allocation. Servo copper drop decreased from 0.123 V to 0.114 V at
4 A, excluding the shunt and ground return. We added motor/servo calculations
to [Supply-path-review.md](Supply-path-review.md); these are geometry-based
screenings, not measured voltage or thermal ratings.

The [CAN geometry audit](CAN-geometry-review.md) records lengths, layer detours
and reference gaps. Bus A crosses bottom-layer 3.3 V and MOSI clearance gaps
near the front CAN circuit. Their refinement, actual branch-current allocation,
ground-return loss and switching-loop review remain open. D807.1 and U1.4 still
have SMD-pad via overlap requiring rerouting or a qualified assembly treatment.

Fresh native ERC/DRC/parity and all 306 targeted checks pass. All 284 electrical
footprints and eight supports match the schematic and placement data. The
saved copper previews and calculation reports reference this board revision.

## Signal completion and feedback returns

We routed the rear degraded-A/B indicators, rear-right lamp and RX-A/RX-B/TX-A
timing markers. We rearranged nearby rear MCU routes, restored the affected
SWD and control connections, and removed unused routing stubs. Footprint
positions, values and local pad geometry are unchanged from revision 58f60c7.
The internal In1.Cu layer remains a ground plane. Existing track/via minimums
and clearance rules are unchanged.

The Pi symbol formerly stacked unused 3.3 V pins 1 and 17 on one schematic
connection. We separated pin 17 and gave both pins individual no-connect
markers. The schematic now has 298 nets; only J70.17's net assignment changed.
Neither Pi 3.3 V pin connects to our regulator or to added PCB copper.

We added explicit 0.20 mm front-copper traces from the three lower feedback
resistors to their regulator ground pins. Zone-excluded checks now verify
all three paths. These branches give the feedback circuits a defined copper
connection; the shared ground pour, switching-loop geometry and noise coupling
still need engineering review.

Three more power transitions now use pairs of 0.70/0.30 mm vias outside their
SMD lands: two sites at D804.1 and one at D802.2. This reduces solder wicking
and adds parallel paths without claiming a current or thermal rating.
D807.1 and the small-signal via at U1.4 remain for assembly review.

D612.1 now connects through a short explicit ground trace to the via at
(70.3325, 91.8) mm in KiCad coordinates. Its local pour contact is disabled
because the crowded fill produced an isolated thermal spoke. This avoids a
solid-pad soldering override. All other pad zone-connection settings are
unchanged. The ground plane and remaining ground connections pass native DRC.

Fresh schematic, placement, routing and fabrication audits agree. Deliberately
removing RX-B copper, merging the unused Pi nets or undoing D612's connection
setting on a temporary copy makes the corresponding checks fail. Updated
copper previews and source hashes accompany this revision.

## Earlier input-power, pull-up and MCU routing

We connected the rear-left lamp signal between U60.24, J603.12 and R650.1.
We rotated encoder pull-ups R804/R807 by 180 degrees to expose their supply
pads, connected them to 3.3 V and restored their encoder-signal branches.
We moved C606 2 mm and rotated it 180 degrees to open the rear MCU fan-out;
its VCAP1 connection stays on F.Cu without vias. We repaired the nearby
R_LEFT_IN2 route and ground branch, then removed unused rerouting stubs.
All other footprint positions, values, local pad geometry and pad nets are
unchanged. Placement data and fit previews match these three changes.

The input circuit now connects the battery header, both physical pad pairs
of the fuse holder, Q1 reverse-polarity circuit, protected input capacitor,
L298 supply/flyback branches, and all three regulator inputs. Main input
tracks use 2.0 mm outer copper, with a 1.2 mm Q1 source escape and a 1.5 mm
regulator feed. Flyback supply branches use 1.0–1.5 mm copper. These are saved
dimensions, not qualified current ratings. Final battery/protection decisions
can still change this circuit.

We replaced five vias inside SMD solder pads (R1.2, U2.3, U3.4, Q1.3 and
C430.1) with two 0.70/0.30 mm vias per site outside the pads. This reduces
solder-wicking exposure and adds parallel paths; it does not establish equal
current sharing or thermal capacity. Other power-pad transitions still need
review, including D807.1, D804.1 and D802.2.

All **292** targeted connection checks pass. The new checks include every
physical input/supply pad, including repeated fuse-holder pin numbers, and
exclude ground pours during traversal. Removing BAT_FUSED copper on a test
copy correctly fails the input check. Fresh native DRC has no ordinary
violations, dangling copper, starved thermals or disconnected GND items;
schematic parity is clear. No thermal override or global rule changed.

At that checkpoint, six rear signals and the stacked unused Pi 3.3 V pins
remained open. The signal-completion revision above resolves those connections.

[Supply-path-review.md](Supply-path-review.md) and
[Return-path-review.md](Return-path-review.md) separate these completed
connections from pending load allocation, voltage/thermal sizing, regulator
feedback returns and CAN reference review.

## Earlier output-power and MCU routing

The preceding revision connected front RX-B timing, console RX, all 5 V load
groups, servo output, motor outputs through their current sensors and
connectors, and flyback pairs. It added ten ground stitches and changed
U80.1's thermal-spoke angle to 0 degrees with 0.20 mm width/gap. These
connections remain checked; the input-feed work described above completes
their previously missing supply connections.

## Earlier MCU, supply and ground routing

We connected six further MCU nets: front console TX, task probe, front-left
LED and degraded-B LED; rear right-encoder A and error LED. Nearby blocking
signals were rerouted and rechecked. Footprint positions and pad nets stayed
unchanged; signal tracks remain 0.20 mm with 0.70/0.30 mm through vias.

Nine new 3.3 V joins connect the main MCU/CAN groups to the logic regulator.
At that checkpoint R804.1 and R807.1 were disconnected; both are now connected.
Seven local 5 V joins connect bypass, sensor, header and pull-up branches;
the later output-power revision completed regulator-to-load connectivity.
Supply width, voltage drop and load-current capability still need review.

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
the exact seven incomplete signal-net names are in `Routing-check.json`.

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
R1.2 to J90 is now connected with 2.0 mm copper. These connections require a final noise/loop and
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
