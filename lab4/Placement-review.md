# PCB placement review

## Current revision — October 28

We selected rear chassis pair A1/A2 after the team confirmed both holes are
unused and accessible. CAD dimensions are 47.870 mm front, 73.01493 mm rear
and 233.21155 mm between rows; team measurements are about 48, 73.45 and
232.85 mm respectively. The PCB is now 120 × 247.21155 mm, extended
13.21155 mm rearward. H1–H4 use 4.0 mm NPTH holes for M3 with 4 mm edge
exclusions; Pi supports remain 2.7 mm with 3 mm exclusions. The earlier
cardboard test used the previous pattern. See
[Mounting-tolerance-revision.md](Mounting-tolerance-revision.md).

All 300 electrical footprints are routed. Pi feed resistance was reduced from
32.668 to 23.000 mΩ without changing component placement. Native checks and
331 targeted connections pass. All support exclusions pass. Current JSON
checks identify the saved PCB hash. Earlier sections below describe dated
snapshots; their old dimensions, socket and routing counts are superseded.

## Earlier review record


26 October 2026. The **routed 120 x 234 mm PCB** is in
`KiCad/Lab4.kicad_pcb`. Its four-hole paper pattern passed the October 24 fit
check, and actual Pi heights were measured. The populated assembly is not
verified and the board is not ready for fabrication. See
[Mechanical-evidence.md](Mechanical-evidence.md) for completed observations.

## Arrangement

The latest routing revision moves C606 from (32,72) to (32,74) mm and rotates
it 180 degrees. R804 and R807 retain their centers and rotate from 90 to
-90 degrees. These changes open their connections without changing pad
nets, values or footprints. The placement checker now verifies preview
rotations as well as centers. All other placements are unchanged.

We placed all 284 schematic components. The five GCT switch footprints replace
their drawing reservations; their geometry and internal contact pairs follow
the manufacturer's A1 drawing. See [Switch-footprint-review.md](Switch-footprint-review.md).
All 298 exported schematic nets are present, and the placed pads retain their
schematic connectivity and reference identities.

The rear MCU, motor-current sensors and L298N/flyback circuits and reserved heatsink area
occupy the rear end. The front MCU and servo-current circuit occupy the front
end. Each node's CAN A and CAN B circuits form separate groups, with exposed
isolation jumpers and test headers. MCU bypass capacitors follow the appropriate
package sides; the detailed current loops still need refinement during routing.
The three regulator groups sit along the front edge, away from the Pi reservation.
We rotated them so their switching pins face the inductors and brought the
local bypass and feedback parts closer. See [Power-stage-review.md](Power-stage-review.md).
Their initial local routing is now connected and passes ordinary DRC. Switching
loop/return-path review and thermal qualification remain; the existing supply
nets are connected. See [Routing-review.md](Routing-review.md).

We changed to a direct connection with the Raspberry Pi 4 **below** our PCB,
component side facing up. J70 is a downward-facing female socket on B.Cu.
This avoids a GPIO cable and keeps our CAN circuits, jumpers and probe headers
on the accessible top side. We moved the cockpit CAN A/B cells into the area
above the Pi. The main PCB can overlap the Pi electrically and mechanically;
we restrict bottom-side components and mounting hardware, not all top parts.

The Pi outline is 85 x 56 mm, at (30,89) mm on our board. Its four holes are
58 x 49 mm apart, with 2.7 mm drills. USB/Ethernet face the right edge;
microSD is on the Pi underside toward the left. USB-C/HDMI face the front.
J70 pad 1 is at (38.37,93.77), pad 2 at (38.37,91.23), pad 39 at
(86.63,93.77), and pad 40 at (86.63,91.23) mm in a top view. All 40 pad
positions are checked, including the bottom-side flip. Electrical nets are
unchanged, and the Pi 3.3 V outputs remain separate from board 3.3 V.

We selected Samtec **ESQ-120-44-L-D** as the connector candidate: 2x20,
2.54 mm pitch, 18.67 mm body height and 4.57 mm solder tails. The local footprint
uses the manufacturer's 1.02 mm finished-hole recommendation and a 1.8 mm pad.
Its simple 3D model represents the body and solder-tail envelope; it is not a
detailed contact model. Availability, assembly process and actual mating must
be checked before procurement/fabrication.

The proposed gap from the Pi's top PCB surface to our PCB underside is 22 mm.
Using the published 8.5 mm GPIO tip height, nominal insertion is
8.5 - (22 - 18.67) = **5.17 mm**, within the socket's 3.68-6.35 mm range.
The reported 18 mm Pi-board-bottom to USB-top height gives 16.4 mm above the
Pi board when its assumed 1.6 mm thickness is subtracted. This leaves **5.6 mm
nominal clearance** to our PCB underside. Top-side through-hole joints over the
Pi (J30/J31/J34/J35) must project no more than 3 mm below our board, leaving
2.6 mm nominal clearance over that USB envelope. A fitted cooler, tolerances and other underside features can change
these results; this is a dimensional calculation, not a measured fit.

We propose 35 mm chassis spacers and four equal 22 mm Pi spacer stacks. With a
1.6 mm assumed Pi PCB thickness, its board underside sits 11.4 mm above the
metal plate, before accounting for underside components, card, screws and wires.
The four Pi supports use hardware no larger than 5.5 mm outside diameter.
The socket carries signals and power; the supports carry mechanical loads.
The October 24 caliper reply reports about 18 mm from Pi board bottom to USB
top and less than 5 mm below the Pi. With the assumed 1.6 mm board thickness,
these leave 5.6 mm above the USB and 6.4 mm below the reported underside
envelope. A 3 mm downward solder tail leaves 2.6 mm nominal clearance above
the USB. These are calculations from measurements, not an assembled fit test.
We keep 35/22 mm as the nominal stack; no repeat height measurement is requested.
Resolve remaining plug, cable, cooler or steering envelopes affecting layout;
verify actual mating at assembly. A provisional
antenna review zone excludes components/copper on both layers, but Wi-Fi and
temperature must still be tested with the actual metal chassis and full stack.
The battery pack needs a separate mounting location; no holder fit is claimed.

The 120 x 234 mm outline allows 7 mm beyond each end row of measured chassis
holes. It is not a demonstrated minimum. The motor stage, power connectors,
encoder conditioning and four LED drivers now have footprints. Heatsink and
cable space are still provisional and may change the final placement.

## Mounting and physical fit

On 23 October the team supplied a [caliper measurement photograph](measurements/chassis-mounting-2026-10-23.jpg)
and confirmed the four **purple-marked** holes as the chassis supports. In that
photo the front is on the left. We label its upper/lower front holes A/B and
upper/lower rear holes C/D. The reported center-to-center dimensions are 50 mm
for A-B, 105 mm for C-D, and 220 mm along the chassis between the two rows.
The team confirmed a measured 4.5 mm chassis-hole diameter, superseding the
image's approximate 4-5 mm label. Measurement uncertainty was not supplied.

The team confirmed both pair midpoints lie on the same centerline. We applied
the pattern using the proposed PCB's rear-left corner as (0,0), x right and y
toward the front. H1/H2 are (7.5,7)/(112.5,7) mm at the rear; H3/H4 are
(35,227)/(85,227) mm at the front. These correspond to photograph C/D/A/B
after rotating the photograph's front-left orientation into this board view.
The 190/30/10 mm image annotations were not needed as extra constraints.

Chassis holes measure 4.5 mm. We propose 3.2 mm PCB clearance holes for M3
hardware with selected washers and female/female spacers. The team confirmed
smooth chassis through-holes; no chassis thread identification is pending.
Actual screw engagement is checked at assembly. The team
reported clearance below the plate for fasteners and motor-wire reach of
roughly 60 mm above it; these reports do not establish the complete stacked fit.
The [mechanical assessment](Mechanical-evidence.md) now gives an 8.75 mm nominal
main-PCB-to-tire vertical separation under its level-ground assumptions, or
3.75 mm with an additional 5 mm sensitivity allowance. It does not qualify the
lower Pi, spacers, cables or complete horizontal steering sweep. Keep the
unpowered full-travel check for assembly rather than requesting another broad
measurement campaign before continuing CAD.

For chassis holes H1-H4 we kept a 3 mm margin outside each hole edge.
For the fixed Pi mounting pattern H5-H8, the proposed clearance radius is 3 mm
from the center, surrounding hardware of at most 5.5 mm diameter. These are
different dimensions: a strict 3 mm margin from the Pi hole edge would require
a 4.35 mm radius and would intersect the standard adjacent GPIO socket body.
The nearest nominal socket-body edge is 3.345 mm from a Pi hole center (1.995 mm
from its drilled edge). Confirm the course interpretation for these Pi supports
before fabrication; we have not claimed the larger clearance is met there.

Bottom placement rule areas avoid the Pi body/ports while allowing top circuitry.
The antenna review zone also excludes copper. Plug/cooler selection limits and
microSD service access are defined in Mechanical-evidence.md. Specific optional
accessories must fit those limits; chassis coordinates are measured and paper-checked.
Antenna performance is a later powered test.

`Placement-fit-template.pdf` is a two-page A4 fit template with a 50 mm scale bar.
Page 1 is the true-size main PCB; page 2 includes a true-size Pi alignment drawing,
a schematic side view and measurement fields. `Pi-stack-side-view.png` shows
the same proposed vertical arrangement.
It is a mechanical check aid, not a drill template. The board outline, proposed
holes and component envelopes are derived from the same placement data.
`Placement-overview.png` is a labeled overview; `Placement-detail.svg` is the
native KiCad plot with pads and references. `Placement-coordinates.csv` contains
footprint anchor coordinates, not measured chassis coordinates.

## Heatsink envelope review

The stock Boyd 6396BG is 41.91 × 25.4 × 25.4 mm. The October 27
[mounting study](Heatsink-mounting-review.md) establishes the anchor geometry,
tab clamp, orientation and nominal vertical fit from drawings. The former
15-courtyard rectangle is historical; it used a different tentative datum.
At the present U80 position, the fin/web clearance screen intersects eight
electrical parts and H1. Moving the sink and U80 by (+3, −3) mm leaves C800,
C802 and J80 in that screen. This candidate is not applied: the footprint,
part movement and affected copper rerouting still need implementation and
all-layer checking. Electrical DRC on the unchanged board does not check the
new heatsink. See Heatsink-mounting-check.json for exact geometry and limits.

## Checks and remaining work

KiCad 10.0.4 loads and plots the PCB. The 26 October DRC, rerun with schematic
parity and excluded findings included, reports:

- 0 placement violations, including courtyard overlap, pad shorts, clearance,
  solder-mask bridges and rule-area conflicts.
- 0 placed-pad net conflicts or symbol-field mismatches.
- 31 missing connections in both the full connectivity count and DRC listing.
  Partial power/CAN/host/signal routing has 15,594 segments, 879 vias and six ground zones across four copper layers.
- 0 missing footprints: all five GCT switches are now placed.

The five switch geometries and contact maps are checked against the GCT A1
drawing. Their schematic fields and BOM entries agree. See `Fabrication-check.json`
and `Fabrication-review.md` for the current submission audit; this placement
result does not authorize fabrication.

The three SOT-563 buck footprints have 0.15 mm adjacent pad gaps. We added a
narrow pad-to-pad exception only within U40, U41 and U42, based on JLCPCB's
published 0.15 mm SMD minimum for the proposed 1 oz process. The project minimum
is 0.15 mm to allow that exception, while the general custom clearance rule and
trace-width rule remain 0.20 mm. This is an explicit manufacturing constraint,
not a suppressed error or a blanket trace-clearance reduction. A 2 oz change
would require a new review. [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/).

`KiCad/Placement-DRC.json` records those results. `Placement-check.json` also
checks the 40 Pi mating positions, net mapping, outline, drill sizes, support
envelopes and nominal insertion. These are software/geometric checks, not
physical tests. Verify motor protection expectations and thermal design,
remaining package/connector assumptions and detailed routing before
fabrication. Follow the converter datasheet's switching-loop and feedback layout
guidance; spreading footprints without routing does not validate a power layout.

## Reproduction

Export the schematic with KiCad 10:

```sh
kicad-cli sch export netlist --format kicadxml -o placement-netlist.xml KiCad/Lab4.kicad_sch
```

Run `generate_placement.py` with KiCad's Python and the installed standard
footprint-library directory. The tool refuses to replace an existing PCB unless
`--replace` is explicitly supplied. Use a different `--output` for comparison
after manual edits. Regenerate the preview with `placement_preview.py`
(Pillow and ReportLab), then run `check_placement.py` and KiCad DRC again.

## Mechanical and layout references

- [Raspberry Pi 4 mechanical drawing, datasheet section 3](https://pip-assets.raspberrypi.com/categories/545-raspberry-pi-4-model-b/documents/RP-008341-DS-1-raspberry-pi-4-datasheet.pdf).
- [Raspberry Pi 4 mechanical drawing with component heights](https://pip-assets.raspberrypi.com/categories/559-mechanical/documents/RP-001185-MD-1-Mechanical%20Drawing.pdf).
- [Samtec ESQ-120-44-L-D](https://www.samtec.com/products/esq-120-44-l-d), [ESQ dimensions and insertion range](https://suddendocs.samtec.com/catalog_english/esw_th.pdf), and [recommended finished-hole pattern](https://suddendocs.samtec.com/prints/esq-sdt.pdf).
- [Hiwonder chassis dimensions](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503): upper plate approximately 270 x 120.5 mm; this does not specify our mounting-hole coordinates.
- [TPS564252 layout guidance, section 8.4](https://www.ti.com/lit/ds/symlink/tps564252.pdf): final switching-loop, capacitor and feedback layout must be checked against the device guidance.
