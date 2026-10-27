# CAN copper geometry review

26 October 2026. We measured the saved board geometry with
`check_can_geometry.py`; [CAN-geometry-check.json](CAN-geometry-check.json)
records the source hash and individual inspection coordinates. This review
does not qualify signal integrity or release the board for fabrication.

## Recorded geometry

| Net | Total copper length, including branches | In2 portion | Signal vias |
| --- | ---: | ---: | ---: |
| CAN_A_H | 256.566 mm | 32.471 mm | 4 |
| CAN_A_L | 251.328 mm | 66.210 mm | 13 |
| CAN_B_H | 242.011 mm | 32.471 mm | 4 |
| CAN_B_L | 236.772 mm | 72.710 mm | 13 |

All four nets use 0.20 mm traces on F.Cu and In2.Cu. Totals include test,
termination and node branches; subtracting H and L totals does not give
end-to-end timing skew. About 52–60% of their length has the opposite line
within 0.65 mm on the same layer. This nearest-line measurement does not
establish parallel coupling, nor is that fraction a pass/fail criterion.

For a straight front-layer pair with 0.20 mm traces and 0.40 mm edge spacing,
the approximate microstrip equations in [TI SLVA531A, section 7.1](https://www.ti.com/lit/an/slva531a/slva531a.pdf)
give 124 ohms differential using our [reference stack](Layer-stack.md):
0.21040 mm dielectric, Dk 4.4 and 0.035 mm copper. This is a nominal geometry
calculation. It omits solder mask, nearby coplanar fill, bends, pad transitions,
In2 routing and fabrication tolerances; it is not a whole-bus impedance claim.

## Ground-reference repair and remaining review

The checker samples trace centerlines at intervals no greater than 0.5 mm,
excluding samples within 1 mm of the same signal's through-hole pads/vias.
The F.Cu routes have In1 ground underneath at the remaining sample points.
In2 is closest to B.Cu, whose ground fill contains other routes.

The previous scan found nine CAN_A_H and three CAN_A_L reference-void samples
near the front CAN circuit. We rerouted the bottom 3.3 V feed around the
affected area and moved the F_MOSI crossing. The updated scan finds **zero
reference-void samples on all four nets** outside the excluded pad/via areas.
The CAN backbone copper itself is unchanged, so the lengths above are unchanged.
Sampling does not establish a continuous reference everywhere.

The replacement 3.3 V feed uses four added vias and a 0.50 mm minimum width;
its length increases from 10.833 mm to 47.303 mm. Clear sections are wider.
The F_MOSI replacement decreases from 10.533 mm to 9.292 mm without added
signal vias. [Supply-path-review.md](Supply-path-review.md) records the
resistance cost of preserving the CAN reference. We also added one ground
stitch near the CAN_B_L transition at (151.4, 209.4) mm after relocating a
ground via away from a solder pad. Coordinates are KiCad board coordinates.

Before release, review unequal layer detours, node/test/termination branches
and the chosen fabrication stack.
The [transceiver layout guidance](https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf)
and [TI CAN physical-layer guide](https://www.ti.com/lit/an/slla270/slla270.pdf)
support short branches and low-inductance reference paths. We have not measured
rise time, reflections, common-mode noise or EMC. Ground-transition distances
remain recorded separately in [Return-path-check.json](Return-path-check.json).

The distance calculation passed analytic checks for a point on a segment,
beside it and beyond its endpoint. Native DRC and targeted connectivity checks
verify connections separately; they do not validate transmission-line behavior.
