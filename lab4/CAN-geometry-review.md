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

## Locations requiring refinement

The checker samples trace centerlines at intervals no greater than 0.5 mm,
excluding samples within 1 mm of the same signal's through-hole pads/vias.
The F.Cu routes have In1 ground underneath at the remaining sample points.
In2 is closest to B.Cu, whose ground fill contains other routes.

The remaining sampled reference gaps are on bus A:

- Around x = 117.85–119.77 mm, y = 201.85–204.40 mm, both CAN lines pass over
  the clearance around a bottom-layer 3.3 V route.
- At approximately (121.60, 210.65) mm, CAN_A_H passes over the clearance
  around bottom-layer F_MOSI routing.

Coordinates use KiCad's board coordinates. These are localized return-path
interruptions to inspect and improve, not proof of a failed CAN link. The
checker found no additional bus-B gaps outside the excluded pad/via areas;
sampling does not establish a continuous reference everywhere.

Before release, reduce these crossings and unequal layer detours, inspect
node/test/termination branches, and confirm the chosen fabrication stack.
The [transceiver layout guidance](https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf)
and [TI CAN physical-layer guide](https://www.ti.com/lit/an/slla270/slla270.pdf)
support short branches and low-inductance reference paths. We have not measured
rise time, reflections, common-mode noise or EMC. Ground-transition distances
remain recorded separately in [Return-path-check.json](Return-path-check.json).

The distance calculation passed analytic checks for a point on a segment,
beside it and beyond its endpoint. Native DRC and targeted connectivity checks
verify connections separately; they do not validate transmission-line behavior.
