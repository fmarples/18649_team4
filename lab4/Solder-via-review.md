# Solder-pad via review

26 October 2026. We checked nominal via drills against the actual SMD copper
land shapes with `check_solder_vias.py`. [Solder-via-check.json](Solder-via-check.json)
records the board hash, via UUIDs, drill diameters and individual locations.
An open hole through a solder land can draw solder away from the component
joint. Passing electrical DRC does not qualify that assembly detail.

## Completed routing changes

The baseline at revision 6164a13 contained 98 intersecting vias across 96 pads.
We moved 70 of those vias outside their solder lands, including D807.1 and
U1.4. The updated board has 28 intersecting vias across 28 pads; none are new
intersections relative to that baseline. Footprints and pad geometry are
unchanged, and native DRC and all 306 targeted connectivity checks pass.

## Remaining routing work

These locations still need a local routing change or an explicitly qualified
fabrication/assembly treatment before release. They are digital design tasks;
new chassis measurements are not needed to investigate them. Coordinates use
KiCad's board coordinates, in millimetres.

| Pad | Net | Via position (x, y), mm |
| --- | --- | --- |
| C140.2 | /GND | 132.1000, 214.7000 |
| C200.2 | /GND | 104.6000, 89.3000 |
| C4.2 | /GND | 65.0000, 77.1000 |
| C503.1 | /+3V3 | 66.2000, 195.0000 |
| C504.1 | /+3V3 | 62.6000, 200.2000 |
| C604.1 | /+3V3 | 62.5000, 101.2000 |
| C604.2 | /GND | 63.1500, 99.1500 |
| C701.1 | /+5V | 60.4000, 120.5000 |
| D613.1 | /GND | 76.2325, 91.3000 |
| R201.1 | /+3V3 | 118.3000, 89.3000 |
| R300.1 | /+3V3 | 101.3000, 148.2000 |
| R301.1 | /+3V3 | 105.1000, 160.2000 |
| R502.2 | /Front zone/F_SELFTEST_BUTTON | 81.8000, 208.2000 |
| R631.2 | /GND | 65.7000, 116.0000 |
| R634.2 | /GND | 77.0500, 116.0000 |
| R711.2 | /Cockpit zone/PI_ERROR_LED_ANODE | 82.8000, 121.1000 |
| R801.2 | /Rear zone/LEFT_ENC_B_IN | 120.1000, 104.2000 |
| U11.2 | /GND | 122.3000, 208.7000 |
| U2.7 | /Rear zone/LEFT_RAW | 61.5000, 77.4000 |
| U2.8 | /+5V | 61.4500, 76.2000 |
| U20.10 | /GND | 112.1000, 87.2000 |
| U21.7 | /Rear zone/R_A_H_LOCAL | 126.2000, 83.1000 |
| U25.7 | /Rear zone/R_B_H_LOCAL | 153.2000, 83.1000 |
| U60.32 | /+3V3 | 75.0000, 110.2000 |
| Y20.2 | /GND | 108.3000, 87.6000 |
| Y24.2 | /GND | 135.3000, 87.6000 |
| Y30.2 | /GND | 95.4000, 158.4000 |
| Y34.2 | /GND | 129.4000, 158.4000 |

## Limits and final assembly review

The checker tests a circular nominal drill against the pad copper shape on
F.Cu or B.Cu. It does not model drill tolerance, solder-mask openings or paste
apertures. Vias moved beside a pad still need the final mask/paste separation
review; zero nominal overlap would not by itself qualify assembly. A tented
via is not automatically a filled and capped via. We have not qualified any
special via treatment or released fabrication files.
