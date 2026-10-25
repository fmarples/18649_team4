# Mechanical evidence and dimensional checks

25 October 2026. We reconciled the October 23–24 measurement photos, team
confirmations and the replies in the [original checklist](https://docs.google.com/document/d/1P07nc_d7xIuWZ1wto0kTwSsNMT-0vlnfMW1e4U4-y5E/edit).
These observations support the design; they do not describe an assembled PCB.

## Completed observations

| Item | Recorded evidence | What it establishes |
| --- | --- | --- |
| Chassis supports | Center-to-center: 50 mm front pair, 105 mm rear pair, 220 mm between rows; pair midpoints aligned. User confirmed 4.5 mm smooth through-holes. | The four chassis coordinates and proposed M3 screw/washer arrangement do not need another measurement. |
| Four-hole fit | The later October 24 photo/report says all four printed-template holes aligned simultaneously with borrowed spacers, approximately 50 mm above the top chassis plate. | Supersedes the earlier opposite-corners-only report. Confirms the paper hole pattern, not all final component/cable clearances. |
| Pi footprint | Pi paper cutout aligned; 2.7 mm Pi holes reported. | Supports the Pi footprint and M2.5 hardware choice. Chassis and Pi hole diameters need not match. |
| Actual Pi height | October 24 caliper reply: about 18 mm from Pi board bottom to USB top; USB body about 16 mm; pins/microSD below the board less than 5 mm. | Supports the 22 mm Pi gap and about 11 mm lower clearance. No repeat caliper campaign is needed for these dimensions. |
| Battery space | A 115 × 50 × 50 mm cardboard envelope fitted between chassis plates; about 51.75 mm usable height reported. | Establishes the tested space, not fit of every battery candidate or of a retaining strap and leads. |
| Cable identification | Servo photos/report: black ground, red old bench supply, white PWM. Pictured motor harness order: motor lead 1, encoder supply, A, B, encoder ground, motor lead 2. | Photos and reported mapping are complete. See Actuator-design.md; adapter continuity and the second harness were not verified by these pictures. |

## Pi stack calculation

We keep the existing **35 mm chassis spacers and 22 mm Pi spacers** as the
nominal design. The borrowed 50 mm spacers were a paper-fit aid, not a new
required board height. These calculations assume a 1.6 mm Pi PCB thickness.

| Calculation | Result | Meaning |
| --- | ---: | --- |
| Pi underside above chassis: 35 − 22 − 1.6 | 11.4 mm | Calculated board clearance; agrees with the comment's approximately 11 mm. |
| Lower clearance after a conservative 5 mm underside envelope: 11.4 − 5 | 6.4 mm | Nominal remaining space before screw tails, wires and tolerances. |
| USB top above Pi top surface: 18 − 1.6 | 16.4 mm | Converts the measured board-bottom datum to the model's board-top datum. |
| USB-to-main-board clearance: 22 − 16.4 | 5.6 mm | Calculated nominal clearance using the reported 18 mm height. |
| With the existing 3 mm maximum downward solder-tail projection: 5.6 − 3 | 2.6 mm | Nominal gap where those tails overlap a USB body. |
| Deliberately use the full 18 mm as an upper-side envelope: 22 − 18 − 3 | 1.0 mm | More pessimistic dimensional case; not a guaranteed tolerance bound. |
| Socket insertion: 8.5 − (22 − 18.67) | 5.17 mm | Within the published 3.68–6.35 mm insertion interval; margins 1.49 mm / 1.18 mm. |

GPIO height comes from the [Pi drawing](https://pip-assets.raspberrypi.com/categories/559-mechanical/documents/RP-001185-MD-1-Mechanical%20Drawing.pdf);
socket dimensions and engagement come from [Samtec](https://suddendocs.samtec.com/catalog_english/esw_th.pdf).
Measurement uncertainty and a complete tolerance stack were not supplied.
No cooler dimensions were supplied; a cooler is not included in this clearance
claim. A different cooler or longer solder tails must be checked against the
available space before installation.

These calculations complete the nominal height assessment. Actual connector
engagement, fastener retention and powered thermal behavior remain assembly
checks. Before freezing the outline/connector positions, only unresolved
geometry needs review: cable exits/plug access, steering sweep and heatsink
installation. Use existing dimensions/drawings where sufficient; a quick
unpowered mock-up is needed only where those cannot establish clearance.
Do not rebuild the Lab 2 circuit to repeat these observations.

## Heatsink and mounting-margin limits

The October 24 message reports TA acceptance of **6396BG** for the preliminary
review and staff follow-up on attachment hardware. Published dimensions are
available; measuring them again is not a prerequisite for placement.
The unresolved issue is its attachment to the L298N and resulting occupied
space: the tentative envelope intersects 15 courtyards. A nominal envelope can
be designed from the drawing, but an unverified mounting method cannot be
declared resolved by adding a margin.

The Pi supports' 3 mm radius from the hole center remains a course-rule
interpretation, not a missing measurement. The adjacent GPIO socket conflicts
with a literal 3 mm margin from the drilled edge. See
[Placement-review.md](Placement-review.md) for the numbers.
