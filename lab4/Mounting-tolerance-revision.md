# Chassis mounting allowance

28 October 2026. We keep the cardboard-verified hole pattern: 220 mm between
rows, 50 mm front-pair spacing and 105 mm rear-pair spacing, with aligned
midpoints. The team reports that Ayaan agreed to use these existing holes
with additional tolerance. This is a team-relayed decision; it is not a claim
that the downloaded chassis CAD now matches the physical car.

H1–H4 are now **4.0 mm finished non-plated round holes for M3 hardware**.
They provide nominal radial adjustment of `(4 − 3)/2 = 0.5 mm` in any
direction, before manufacturing and screw tolerances. All four centers are
unchanged. This allowance covers small alignment errors, not an unbounded
CAD discrepancy. A slot would provide additional movement along one axis,
but we do not have a measured directional offset that calls for one.

We increased the chassis exclusion to **4 mm from each finished hole edge**:
a 6 mm clear radius from the center. Components, tracks, vias and copper
fills on all four layers stay outside it. The 7 mm OD nylon washers bridge
the enlarged PCB holes and the measured 4.5 mm chassis holes. The specified
6 mm AF standoffs also have adequate bearing overlap at nominal alignment.
Use the listed washers and check retention during assembly.

The Pi holes remain 2.7 mm with a **3 mm edge exclusion**, a 4.35 mm clear
radius. Their fixed connector/mounting geometry does not need the chassis
adjustment allowance. A 6 mm edge exclusion is not a free improvement:
on the chassis it intersects HS80/D800/Q1 and routes; on the Pi it intersects
the GPIO socket and other parts. We chose the larger margin where it fits
without moving those functions.

The all-layer rule areas exclude traces, vias and fills. KiCad's empty NPTH
pad object is not treated as electrical copper; `check_mounting_clearance.py`
separately checks every electrical pad and component courtyard. No electrical
clearance rule was reduced. A short servo-power detour preserves its original
2 mm width. Final hardware retention and a rigid-board fit remain assembly
checks; no new chassis measurement is requested for this selected pattern.

Manual drilling is a fallback, not a fabrication instruction. Any later
enlargement must preserve the actual all-layer copper and component margins,
washer bearing area and board-edge strength.
