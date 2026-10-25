# Initial regulator routing

25 October 2026. We started copper routing in the three regulator groups while
the battery, motor-protection and heatsink decisions are pending. The saved
PCB contains **206 track segments, 45 through vias and four filled ground
zones**. This is an initial routing revision, not a fabrication release.

## What is connected

For each TPS564252, we connected VIN to its local input capacitors and enable
divider; SW to the inductor; the inductor output to both output capacitors,
the test header and the feedback divider. The feedback, enable and power-good
nodes are connected locally. Ground pads have nearby vias into the bottom
ground plane, with local top-layer ground copper. A separate output-sense
trace runs from the output capacitor to the divider, away from SW.

The initial main power paths use 0.6–1.6 mm tracks after short 0.2 mm escapes
from the small IC pads. Signal routes use 0.2–0.25 mm tracks. Ground vias are
0.8 mm diameter / 0.4 mm drill; signal vias are 0.7 / 0.3 mm. These dimensions
are recorded design choices, not verified current or temperature ratings.
The existing 0.20 mm general clearance rule is unchanged.

All footprint positions, orientations, pad nets and schematic parts are
unchanged from the preceding placement revision. The board-wide input/output
feeds and two 3.3 V power-good pull-ups still need routing. The feedback ground
currently joins the common plane; review its Kelvin return and switching-current
paths before freezing these power stages. Effective capacitance, copper loss,
thermal spreading and regulator transient behavior are not qualified.

## Checks and progress

- `check_routing.py` walks KiCad's physical copper connectivity graph. All 21
  local groups (seven per regulator) connect their required pads through actual
  copper. This is independent of the schematic's net labels.
  Removing one SW escape in a temporary test copy correctly fails U40-to-L1
  connectivity, despite the pads still carrying the same net name.
- Fresh DRC reports zero ordinary violations; ERC and schematic parity are
  checked in [Fabrication-check.json](Fabrication-check.json). Rules were not
  relaxed for this routing pass.
- KiCad's full saved-board connectivity count fell from **763 to 648** missing
  connections. The earlier 499 figure was the capped DRC report length, not the
  total. KiCad 10's [DRC engine source](https://github.com/KiCad/kicad-source-mirror/blob/10.0/pcbnew/drc/drc_engine.cpp)
  limits that category to 499 entries. The audit now records both counts.
- [Routing-check.json](Routing-check.json) records connection groups, widths,
  via sizes and the PCB hash. The native front/back copper plots are
  [Routing-front.svg](Routing-front.svg) and [Routing-back.svg](Routing-back.svg).

We still need to route MCU/CAN bypass, clocks and local signals, the separate
CAN A/B backbones, sensing and actuator circuits, and board-wide power
distribution. These settled local circuits can proceed before the open
battery/heatsink answers. Reserve the affected input-power and L298 areas for
their specific decisions. Finish power-loop/return-path review and a complete
fresh audit before producing manufacturing files.

The power-layout basis is the [TI TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf).
See [Power-stage-review.md](Power-stage-review.md) for the component calculations
and their limits. No new-board electrical or thermal measurement is claimed.
