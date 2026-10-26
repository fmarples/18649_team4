# Power, MCU, CAN and signal routing

25 October 2026. We have routed the local MCU/CAN circuits, both CAN backbones,
the three host interfaces and 76 sensing/control/diagnostic nets. The latest
pass adds rear UART TX/RX, eleven 3.3 V branch joins, both servo-shunt sense
inputs and the servo regulator-to-shunt feed. It also adds a front ground
reference and ground stitching. **31 MCU signal nets and board-wide power
paths are still incomplete.**

The saved PCB has **10,332 track segments, 703 through vias and five filled
ground zones**. Missing connections fell from **171 to 128** in this pass
(the preceding signal pass reduced 305 to 171). This is a partial routing
revision, not a fabrication release. All footprint positions, values and pad
nets are unchanged. Two old 3.3 V segments were rerouted for rear UART clearance;
four old segments and one via forming their unused branch stub were removed.
All other pre-existing copper objects remain.

## Connections completed in this revision

For each MCP2515, we connected its crystal and load capacitors, local bypass,
reset network, inactive RTS inputs and chip-select pull-up. TXD/RXD now reach
the transceiver and test header. The transceiver has a local bypass connection,
ground connections and CAN H/L connections to its isolation header. Each node's
backbone-side test pins and, where fitted, termination jumper/resistor are
connected locally. Both CAN A/B backbones now connect the rear, cockpit and
front nodes. The main runs are front-layer pairs with 0.20 mm tracks and
0.60 mm center spacing (0.40 mm copper gap). Bus A goes around the Pi support
and header; Bus B follows the right edge. Branch fanouts use both layers.
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
The MCU and CAN supply groups still need their board-wide 3.3 V feeds.

Schematic values, pin assignments, package identities, mounting holes and
regulator copper are unchanged. No battery or heatsink decision was needed for
these local routes. The new local signal tracks are 0.20 mm wide; vias are
0.70 mm diameter with 0.30 mm drills. The general 0.20 mm clearance and existing
fabrication rules are unchanged.

## Host interfaces

Both STM32s and the Pi now connect to their two MCP2515 controllers. We kept
the Lab 3 pin assignments: shared SCK/MISO/MOSI and independent CS/INT per
controller. The six CS pull-ups remain on their corresponding chip-select
nets. Short pin escapes lead to through vias; longer connections use both
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
the MCU debug, indicator and timing-header wiring. IN2/IN3, the fourth encoder
output and several MCU diagnostic/indicator pins are still open. The exact
31 incomplete signal-net names are in `Routing-check.json`.

Signal tracks are 0.20 mm wide with 0.70/0.30 mm through vias. The switching
regulator cells and mounting/antenna reservations are preserved. New routes
do not change the schematic or pin map. We connected both physical ground
contacts of SW70 and added local ground bridges where signal tracks divided
the plane. The latest ground-connection choices are recorded below.

## Supply branches, servo sensing and ground reference

Rear UART TX/RX now connect U60 pins 44/45 to J602 pins 1/2. Eleven checked
3.3 V branch joins use mostly 0.80 mm copper, with two 0.50 mm connections.
These are joins between local groups, not proof that every group reaches the
regulator; the C600-to-J600 supply branch and other board-wide feeds remain open.

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
  **230 targeted connection checks** pass: 21 regulator, 76 local CAN, 14 MCU,
  four backbone nets, 21 host-interface nets, 76 additional signal nets, eleven
  supply branches, two shunt inputs, one servo power-feed connection, two UART
  nets and two filter-ground connections. Each backbone net reaches all eight required
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
- ERC on the unchanged schematic, fresh ordinary DRC and schematic parity
  have zero findings. The remaining
  128 unconnected items are reported as fabrication blockers in
  [Fabrication-check.json](Fabrication-check.json), not suppressed.
  Whole-board routing is unfinished; ground/return continuity remains a release check.
- All 284 electrical footprints and their pad nets match the schematic.
  Placement coordinates and previews match the saved board; all original
  regulator track/via objects and all non-CAN footprint positions are preserved.
- [Routing-check.json](Routing-check.json) records connection groups, clock
  lengths, widths, via sizes and the source hash. Native copper plots are
  [Routing-front.svg](Routing-front.svg) and [Routing-back.svg](Routing-back.svg).

KiCad 10 caps its DRC unconnected list at 499 entries; our audit also records
the full connectivity count. Both now report 128. The earlier regulator-only
revision had 648 missing connections, although its DRC list stopped at 499.
See the [KiCad DRC engine source](https://github.com/KiCad/kicad-source-mirror/blob/10.0/pcbnew/drc/drc_engine.cpp).

## Remaining routing

Board-wide power/load-current paths and 31 MCU-related signal nets still need
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
