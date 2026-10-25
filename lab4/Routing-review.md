# Local power, MCU and CAN routing

25 October 2026. We routed the local circuits around both STM32s and all six
CAN interfaces, preserving the three previously routed regulator groups.
The saved PCB has **2,214 track segments, 275 through vias and four filled
ground zones**. The full missing-connection count fell from **648 to 345**.
This is a partial routing revision, not a fabrication release.

## Connections completed in this revision

For each MCP2515, we connected its crystal and load capacitors, local bypass,
reset network, inactive RTS inputs and chip-select pull-up. TXD/RXD now reach
the transceiver and test header. The transceiver has a local bypass connection,
ground connections and CAN H/L connections to its isolation header. Each node's
backbone-side test pins and, where fitted, termination jumper/resistor are
connected locally. **The long CAN A/B backbones between nodes are not routed.**

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
  **111 local connection groups** pass: 21 regulator, 76 CAN and 14 MCU groups.
  It also checks the duplicated physical switch contacts and front-only clock
  copper. Removing U10's OSC1 copper in a temporary copy correctly causes a
  failure even though the pads retain their schematic net names.
- Fresh ERC, ordinary DRC and schematic parity have zero findings. The remaining
  345 unconnected items are reported as fabrication blockers in
  [Fabrication-check.json](Fabrication-check.json), not suppressed.
- All 284 electrical footprints and their pad nets match the schematic.
  Placement coordinates and previews match the saved board; all original
  regulator track/via objects and all non-CAN footprint positions are preserved.
- [Routing-check.json](Routing-check.json) records connection groups, clock
  lengths, widths, via sizes and the source hash. Native copper plots are
  [Routing-front.svg](Routing-front.svg) and [Routing-back.svg](Routing-back.svg).

KiCad 10 caps its DRC unconnected list at 499 entries; our audit also records
the full connectivity count. Both now report 345. The earlier regulator-only
revision had 648 missing connections, although its DRC list stopped at 499.
See the [KiCad DRC engine source](https://github.com/KiCad/kicad-source-mirror/blob/10.0/pcbnew/drc/drc_engine.cpp).

## Remaining routing

Host SPI/chip-select/interrupt wiring, the long CAN A/B backbones, board-wide
power, sensing, actuator and remaining probe/indicator signals still need
routing. Review CAN pair geometry, continuous reference copper, return paths
and power-loop/thermal behavior before layout freeze. These digital routes
can continue without new lab measurements. Battery/input-power, motor-fault
protection and heatsink choices affect their specific areas.

Design references: [MCP2515 datasheet](https://www.microchip.com/content/dam/mchp/documents/APID/ProductDocuments/DataSheets/MCP2515-Family-Data-Sheet-DS20001801K.pdf),
[SN65HVD23x layout guidance](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf),
and [TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf).
See [Power-stage-review.md](Power-stage-review.md) for regulator calculations.
No new-board electrical, oscillator or thermal measurement is claimed.
