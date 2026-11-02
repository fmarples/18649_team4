# November 2 — Anson PCB review changes

We checked [Anson's shared review](https://docs.google.com/document/d/1KRUg6gwJZ7ZEjsMl1iB4o16e8cOBPVASS1JjuUOm5Sw)
against the `4895895` board, rather than assuming every comment described the
latest revision. The group names were already present. The schematic, fuse
label, connector placement and local routing still benefited from changes.

## Review disposition

| Review item | Result in this revision |
| --- | --- |
| Schematic readability / reference schematic | Redrew the four circuit sheets into functional sections with connected local circuits, readable signal flow and section labels. Front/rear sheets shrink from A0 to A1; power/cockpit use A2. Keep the five-sheet hierarchy and zoom the vector PDF for component detail. |
| F1 still says rating TBD | Replaced that label in schematic, PCB and circuit BOM with **10A / 32V (0297010.L)**, matching the existing removable fuse candidate. The 3568 holder identity and purchasing quantities are unchanged. This label does not qualify fuse coordination or per-motor protection. |
| Missing group names | Already resolved in the prior board. All three names remain; they move to the bottom silkscreen to make room for the rear clamp placement. **649 Team 4** remains on top. |
| Motor / battery connectors | Moved J80 to the rear-left edge near the left motor cable exit. J81 remains in the rear motor area and J40 remains accessible from above near the battery-lead route. Moved J80's connection legend with it. Cable reach/retention still needs checking during assembly. |
| Bypass capacitors close to supply pins | Reviewed 30 MCU, CAN, sensor, driver and LDO supply paths, plus the existing buck input/output/feedback checks. Moved C500, C800 and C801 to the underside near their supply connections. All other local bypass placements stay. See the measured path table below. |
| CAN_H / CAN_L together where possible | Rerouted Front B (U15/J14) and Pi B (U35/J34) with adjacent main runs on In2 and short pad escapes; each line now uses one via. The four other local interfaces retain their routes. This is a partial geometry improvement, not a claim that every local pair is coupled or that CAN signal integrity is qualified. |
| Flyback diodes near motor connectors | Moved all eight clamps into the rear connector area, retaining the November 1 motor-side net correction. Added direct wide phase/return connections and extended the ground fill into the existing rear board extension. Removed obsolete routing tails. |

## Measured routing changes

The following are shortest **whole-conductor-item** paths in saved CAD, counting
1.6 mm for each via. They are useful comparisons, not extracted electrical
lengths or proof of transient behavior.

| Supply pin → bypass | Before, mm / vias | After, mm / vias |
| --- | ---: | ---: |
| U50.19 → C500.1 | 11.483 / 2 | 6.607 / 1 |
| U80.4 → C800.1 | 67.307 / 3 | 1.600 / 0 |
| U80.9 → C801.1 | 15.106 / 0 | 1.800 / 0 |

| Clamp → connector | Before, mm | After, mm |
| --- | ---: | ---: |
| D800.2 → J80.1 | 36.660 | 12.481 |
| D801.1 → J80.1 | 42.742 | 16.181 |
| D802.2 → J80.2 | 43.590 | 14.300 |
| D803.1 → J80.2 | 51.845 | 18.000 |
| D804.2 → J81.1 | 53.860 | 14.883 |
| D805.1 → J81.1 | 57.254 | 19.583 |
| D806.2 → J81.2 | 61.855 | 24.452 |
| D807.1 → J81.2 | 87.646 | 29.152 |

Front-B H/L proximity within 1 mm on the same layer rises from 2.9%/1.1%
to 93.4%/83.2%; Pi-B rises from 1.8%/5.6% to 90.2%/70.4%. The tradeoff is
longer local paths, especially Front B: 37.867/44.375 mm instead of
28.627/25.012 mm. Nearest-line proximity is not a coupling or impedance
measurement. Short connector escapes and the other four interfaces are not
fully paired; retain these limitations in staff review. Backbone routing is
unchanged. The enlarged course-rule antipads remain visible in the CAN
reference-plane report; they are not continuous reference copper.

## Assembly and verification

**C500, C800 and C801 are now bottom-side SMT.** Install them before the
through-hole hardware obstructs access. Their courtyards clear bottom parts,
the Pi reservation and protruding through-hole lands. The check also finds
zero via-drill/SMD-land intersections and no nominal drills within the
0.15 mm solder-opening review gap. The populated assembly is not tested.

The support holes, Pi socket, heatsink anchors, outline, stack, component
identities and pad nets are unchanged. We preserved all **1,077 pin-to-net
assignments** through the schematic redraw. D713's thermal-spoke angle is
45 degrees; no new solid-pad connections were introduced. Ground islands
without connections are removed by the zone-fill settings.

Fresh ERC, native DRC, schematic parity and unconnected counts are zero.
All 331 targeted routing checks and the 282-component package checks pass.
Placement, heatsink/support clearances, supply/return paths, ground/Pi
meshes and capacitor/power screens were refreshed against the saved board.
The calculation assumptions and required bench commissioning are unchanged.

See [the exact comparison](November2-Anson-review-check.json),
[native checks](Fabrication-check.json), [bypass/trace paths](Digital-geometry-check.json)
and [matching exports](review-package/manifest.json). The original `6945466`
submission remains historical; the team linked `4895895` to Anson on
November 2. These new files have not been sent or submitted. Staff acceptance,
ordering, assembly and powered validation are separate unfinished steps.
