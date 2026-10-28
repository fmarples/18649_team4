# Mechanical evidence and dimensional checks

Updated 28 October 2026. We reconciled the October 23–24 measurement photos, team
confirmations and the replies in the [original checklist](https://docs.google.com/document/d/1P07nc_d7xIuWZ1wto0kTwSsNMT-0vlnfMW1e4U4-y5E/edit).
These observations support the design; they do not describe an assembled PCB.

The October 28 [chassis CAD comparison](Chassis-CAD-review.md) found a reference
conflict after correcting the rear-hole selection: the revised CAD features
give 222.246 mm between rows and 92.860 mm rear-pair spacing, versus recorded
220 mm and 105 mm. The earlier 238.650 mm result used the wrong rear pair.
The successful four-hole paper
fit below remains completed evidence, and the PCB geometry is unchanged.
Resolve the model's correspondence/revision before claiming CAD confirmation
of the actual chassis; no new general measurement session is requested.

## Completed observations

| Item | Recorded evidence | What it establishes |
| --- | --- | --- |
| Chassis supports | Center-to-center: 50 mm front pair, 105 mm rear pair, 220 mm between rows; pair midpoints aligned. User confirmed 4.5 mm smooth through-holes. | Remains the physical basis for the four PCB coordinates and proposed M3 screw/washer arrangement. The newly discovered CAD-reference conflict needs reconciliation, rather than an automatic repeat measurement. |
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
the shortened socket covering Pi pins 3–38 in this design; a USB-C power cable is not part of the normal
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

## Implemented heatsink and mounting margins

The October 27 drawing-based heatsink installation is now on the PCB.
Its anchor pattern, local routing and fin/web clearances pass the recorded
checks; no repeat measurement is requested. See Heatsink-mounting-review.md.

The user directed 3 mm from the finished hole edge at all chassis/Pi supports,
including copper. The shortened ESQ-118-44-L-D socket provides 4.535 mm
from the nearest Pi hole edge and 3.135 mm from 5.5 mm OD hardware.
The old 0.595 mm hardware clearance and 1.005 mm rule shortfall describe
the superseded 40-contact socket. The new socket covers Pi3–38 only;
assembly must align its first pair to Pi3/4. See Mounting-and-encoder-revision.md.
