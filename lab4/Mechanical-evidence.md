# Mechanical evidence and dimensional checks

Updated 27 October 2026. We reconciled the October 23–24 measurement photos, team
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

These calculations complete the nominal height assessment. We do not request
another height measurement or a pre-assembly lab visit for it. Actual connector
engagement, fastener retention and powered thermal behavior are assembly checks.
The reproducible [dimensional check](check_mechanical_fit.py) reads the saved
board and produces [Mechanical-fit-check.json](Mechanical-fit-check.json).
Its results are calculated dimensions, not additional physical observations.

## Port, cable and steering assessment

We can continue the design using explicit accessory envelopes. An unspecified
plug or cooler cannot be declared compatible, but it need not stop placement:
we choose accessories to fit the available space. The Pi is powered through
the 40-pin socket in this design; a USB-C power cable is not part of the normal
vehicle power path. USB/Ethernet cables are optional service accessories.

| Item | Drawing-based result and design constraint | Status |
| --- | --- | --- |
| USB/Ethernet access | The Pi board edge is 5 mm inside the main PCB edge. The existing bottom-side port corridor opens to that edge. Keep any plug/boot portion under the main PCB within 18 mm above the Pi top surface; with tails at most 3 mm, this leaves 1 mm nominal vertical space. A plug extending horizontally beyond the main board is allowed. | Corridor and height limit defined; a particular cable is not qualified until its drawing satisfies the envelope. |
| Cooler | Total installed cooler height, including its interface, must fit the same 18 mm upper-side envelope wherever a 3 mm solder tail overlaps. A cooler is not presently selected or included in the BOM fit claim. | Selection constraint defined; no measurement needed for a future part with a drawing. |
| microSD access | The Pi's left edge is 30 mm inside the main board. The saved lower-side access corridor extends to the left board edge. The calculated 6.4 mm residual lower clearance supports card-level access; it does not guarantee fingertip access. Install the card before stacking and use a thin card-handling tool for later service if required. | Service method defined; no requirement to fit a hand in the gap. |
| Motor/servo leads | Reported motor lead reach is about 60 mm above the chassis, versus a 35 mm PCB underside height. The 25 mm difference must also accommodate PCB/connector height and bends; it is not proof that every lead reaches every connector. Use the already planned adapter harnesses, cut to route with slack and secured away from moving parts. | No board change or repeat photograph needed. Actual adapter length/continuity is checked when making it. |
| Main PCB above tires | The recorded 75 mm tire diameter and 51.75 mm interplate gap give the vertical screen below. | Nominal main-board clearance calculated; complete vehicle sweep is an assembly check. |

For the tire screen, assume upright wheels on level ground and a rigid chassis.
Conservatively set lower-plate ground clearance and plate thickness to zero;
both positive dimensions would raise the main PCB. Its lowest allowed solder
tail is then at least 51.75 + 35 − 3 = **83.75 mm above ground**, compared with
the nominal tire top at 75 mm: **8.75 mm separation**. Even allocating another
5 mm for combined dimensional/deflection uncertainty leaves **3.75 mm**.
That 5 mm is a sensitivity allowance, not a measured or guaranteed tolerance.
The 75 mm figure is the team's recorded wheel diameter in
[HARDWARE.md](../doc/HARDWARE.md); the 51.75 mm figure is the October 24 report.
This vertical result does not depend on the steering angle while tires stay
upright on the same level surface.

The screen covers the main PCB and its limited solder tails. It does not cover
the lower Pi, long chassis spacers, loose cables, tire camber or obstacle travel.
The [chassis drawings/photos](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503)
do not dimension all steering pivots, stops or cable paths, so we do not claim
a mathematically complete swept-volume check. We retain the present outline
and stack as the nominal design, route cables inboard, and keep a full left/right
unpowered steering check for assembly. There is no new general measurement
request or requirement to dismantle Lab 3 before continuing CAD.

## Checks that actually require hardware

After assembly, confirm socket mating, screw engagement/retention, adapter
continuity/polarity and unpowered full steering travel with the installed
cables. Loaded voltage, ripple, noise, radio performance and temperature are
powered bring-up tests. Calculations support design choices but cannot report
those outcomes for a board that has not been built. They are not pre-fabrication
measurement tasks in the October 29 checklist.

## Heatsink and mounting-margin limits

The October 24 message reports TA acceptance of **6396BG** for the preliminary
review and staff follow-up on attachment hardware. Published dimensions are
available; measuring them again is not a prerequisite for placement.
The October 27 [mounting review](Heatsink-mounting-review.md) now specifies
the two soldered anchors, M3 tab clamp, thermal interface and nominal vertical
fit from Boyd/ST drawings. No new measurement is needed to determine that
method. The old 15-courtyard rectangle is superseded by a drawing-based
fin/web screen and a nearby placement candidate. Installing the footprint,
moving the affected parts and rerouting their copper remain digital work;
the actual assembled fit and temperature have not been tested.

The saved socket body is **3.345 mm from the nearest Pi hole centers**. This
corrects the older 3.337 mm center-distance text; the 1.995 mm edge distance was
already correct. A 5.5 mm maximum hardware diameter leaves **0.595 mm nominal
body clearance**. However, the 2.7 mm hole plus a literal 3 mm edge margin needs
radius 1.35 + 3 = 4.35 mm, exceeding the available distance by **1.005 mm**.
Thus physical nominal fit and the course-rule interpretation are different
questions. No measurement or conservative estimate changes that rule conflict.
We still need the TA's interpretation, or a deliberate mounting redesign, before
claiming compliance. See [Placement-review.md](Placement-review.md).
