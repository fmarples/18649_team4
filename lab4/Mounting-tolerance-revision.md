# Chassis mounting revision — October 28

We selected **A1/A2**, the outer two holes in the four-hole row above the rear chassis screws. The team confirmed both are present, unused and accessible underneath. The team measured **73.45 mm** between them and **232.85 mm straight between the front and rear rows**, and instructed us to use the corresponding CAD nominal values.

| Dimension | Selected PCB/CAD nominal | Team measurement |
| --- | ---: | ---: |
| Front pair | 47.870 mm | Approximately 48 mm |
| Rear pair A1/A2 | 73.01493 mm | 73.45 mm |
| Row separation | 233.21155 mm | 232.85 mm, straight between rows |
| Rear chassis holes | 3.2 mm in CAD; M3 hardware | Present, unused and accessible; diameter follows CAD |
| PCB outline | 120 × 247.21155 mm | New outline, not the earlier cardboard pattern |

We extended the PCB **13.21155 mm rearward**. Existing electrical component positions are unchanged. The fixed KiCad (40,40) mm datum is retained: the new rear edge is Y=26.78845 mm, the other edges remain X=40/160 and Y=274 mm. Placement coordinates may therefore have negative Y relative to the original datum.

| Support | KiCad X / Y (mm) | PCB drill |
| --- | --- | --- |
| H1, rear A1 | 63.49254 / 33.78845 | 4.0 mm NPTH |
| H2, rear A2 | 136.50747 / 33.78845 | 4.0 mm NPTH |
| H3, front left | 76.065 / 267 | 4.0 mm NPTH |
| H4, front right | 123.935 / 267 | 4.0 mm NPTH |

Rear supports sit 7 mm from the new PCB edge. We keep **4 mm from each finished hole edge** free of components, tracks, vias and filled copper on all layers: a 6 mm exclusion radius. The rear circles end 0.212 mm before the former PCB edge, so the hole change needs no existing component or trace relocation. Old rear exclusions are removed and zones are refilled. Front holes move inward 1.065 mm each and also retain 4 mm edge exclusion.

**M3 supports** match the CAD's 3.2 mm rear chassis holes. The **4.0 mm PCB drills** provide intentional adjustment clearance; they are not the chassis diameter. Around a nominal 3 mm screw, radial adjustment is 0.5 mm. Holding the front row fixed, the measured rear-width difference contributes 0.218 mm per side and the row difference contributes 0.362 mm, for a combined offset of about **0.422 mm**. This fits the nominal allowance before measurement, screw and drilling tolerances. Use the listed 7 mm OD washers and check rigid-board fit and retention during assembly. No slot or manual drilling is required by the selected nominal geometry.

Pi H5–H8 remain 2.7 mm holes for M2.5 hardware with a 3 mm hole-edge exclusion. Nominal 35 mm chassis and 22 mm Pi spacers are unchanged.

We do not need the farther rear pair to create mounting clearance. The selected extension already separates the rear hole exclusions from the original circuit area. With a 7 mm outside-diameter washer, the 6 mm exclusion radius leaves 2.5 mm beyond the centered washer edge (2.0 mm at the nominal 0.5 mm screw offset). A farther pair would lengthen the PCB and require verification of different chassis holes without resolving an existing clearance conflict. We keep the selected A1/A2 pair and the current electrical component positions.

## Superseded measurements

The earlier cardboard test used 50/105/220 mm. It remains a completed historical paper fit, not a test of this revised pattern. Later rear width 106.8 mm, row distance 222 mm and same-side distances 225.77/225.08 mm refer to the **old rear holes**. Their centered geometry was inconsistent by 1.13–1.82 mm in the same-side cross-check; we have not averaged them into A1/A2.

See [Chassis-CAD-review.md](Chassis-CAD-review.md), [Rear-mounting-selection.json](Rear-mounting-selection.json) and the updated [full-size template](Placement-fit-template.pdf).
