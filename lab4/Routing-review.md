# Power, MCU, CAN and signal routing

25 October 2026. We routed the local circuits around both STM32s and all six
CAN interfaces, joined the three zones through both CAN backbones, and routed
all three hosts' SPI, chip-select and interrupt connections. We then connected
76 additional sensing, control, debug and indicator nets. The previously
routed copper and all footprint positions are preserved.
The saved PCB has **9,961 track segments, 631 through vias and four filled
ground zones**. The full missing-connection count fell from **305 to 171** in the latest pass
(the earlier regulator-only board had 648).
This is a partial routing revision, not a fabrication release.

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
schematic pin nets and all previously checked track/via objects are preserved.
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
33 incomplete signal-net names are in `Routing-check.json`.

Signal tracks are 0.20 mm wide with 0.70/0.30 mm through vias. The switching
regulator cells and mounting/antenna reservations are preserved. New routes
do not change the schematic or pin map. We connected both physical ground
contacts of SW70 and added local ground bridges where signal tracks divided
the plane. J501.3, J601.3/J601.6, J704.2 and J70.20 use solid ground-plane
connections because the surrounding routes starved their thermal spokes.
These pins will require more soldering heat. The global minimum-spoke rule
is unchanged; these five pads deliberately use a different connection style.
No load-current rating or signal-integrity qualification is inferred
from these connections. Current-shunt Kelvin inputs and high-current load
paths remain a separate routing/review task.

The remaining MCU signals need a revised local fanout, potentially including
nearby bypass placement. These are CAD tasks; they do not require new lab
measurements. Trial changes that could not reconnect every affected net were
discarded. The saved revision retains every earlier track/via object.

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
  **212 targeted connection checks** pass: 21 regulator, 76 local CAN, 14 MCU,
  four backbone nets, 21 host-interface nets and 76 additional signal nets. Each backbone net reaches all eight required
  pads across the three zones, with termination on the bus side of isolation.
  It also checks the duplicated physical switch contacts and front-only clock
  copper. Removing U10's OSC1 copper in a temporary copy correctly causes a
  failure even though the pads retain their schematic net names. A second
  temporary fault test removes front-host SCK copper and correctly fails
  the new U50 host-SCK check. Removing LEFT_ADC copper from another temporary
  copy correctly fails its new signal-endpoint check despite unchanged pad nets.
  The duplicate switch-pad check now compares physical pad identities; it
  detected SW70's separated ground contacts before they were connected.
- Fresh ERC, ordinary DRC and schematic parity have zero findings. The remaining
  171 unconnected items are reported as fabrication blockers in
  [Fabrication-check.json](Fabrication-check.json), not suppressed.
  The remaining ground count is 55, compared with 56 before this pass.
  Whole-board routing is unfinished; ground/return continuity remains a release check.
- All 284 electrical footprints and their pad nets match the schematic.
  Placement coordinates and previews match the saved board; all original
  regulator track/via objects and all non-CAN footprint positions are preserved.
- [Routing-check.json](Routing-check.json) records connection groups, clock
  lengths, widths, via sizes and the source hash. Native copper plots are
  [Routing-front.svg](Routing-front.svg) and [Routing-back.svg](Routing-back.svg).

KiCad 10 caps its DRC unconnected list at 499 entries; our audit also records
the full connectivity count. Both now report 171. The earlier regulator-only
revision had 648 missing connections, although its DRC list stopped at 499.
See the [KiCad DRC engine source](https://github.com/KiCad/kicad-source-mirror/blob/10.0/pcbnew/drc/drc_engine.cpp).

## Remaining routing

Board-wide power/load-current paths, Kelvin shunt inputs and 33 MCU-related
signal nets still need routing. Review CAN pair geometry, continuous reference copper, return paths
and power-loop/thermal behavior before layout freeze. These digital routes
can continue without new lab measurements. Battery/input-power, motor-fault
protection and heatsink choices affect their specific areas.

Design references: [MCP2515 datasheet](https://www.microchip.com/content/dam/mchp/documents/APID/ProductDocuments/DataSheets/MCP2515-Family-Data-Sheet-DS20001801K.pdf),
[SN65HVD23x layout guidance](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf),
and [TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf).
See [Power-stage-review.md](Power-stage-review.md) for regulator calculations.
No new-board electrical, oscillator or thermal measurement is claimed.
