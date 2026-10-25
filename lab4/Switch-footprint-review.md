# GCT reset and self-test switch footprint

We verified and added the five SWT0210-045026GSA footprints on October 25:
SW50/SW60 (reset) and SW51/SW61/SW70 (self-test). They replace the five drawing
reservations in the unrouted placement study. The switch nets and course part
numbers are unchanged.

## Drawing and dimensions

We used the GCT manufacturer drawing, revision A1, dated 02/09/25, sheet 1,
[hosted by DigiKey](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8937/SWT0210.pdf).
The recommended land pattern is explicitly viewed from the component side.

| Feature | Drawing value / implementation |
| --- | --- |
| Body | 4.50 × 4.50 mm, ±0.10 mm |
| Button height above PCB | 4.50 ±0.10 mm |
| Four solder pads | 1.40 × 1.40 mm square |
| Horizontal pad centers | x = −3.30 and +3.30 mm |
| Vertical pad centers | y = −1.50 and +1.50 mm |
| Horizontal pad edges | 8.00 mm outside span, 5.20 mm inside gap |
| Vertical pad edges | 4.40 mm outside span, 1.60 mm inside gap |
| Local courtyard | 8.50 × 5.10 mm, includes clearance beyond pads/body |

The pad-center calculation is (8.00 − 1.40)/2 = 3.30 mm horizontally and
(4.40 − 1.40)/2 = 1.50 mm vertically. The drawing's 8 mm dimension is the
**outside pad span**, not center-to-center pitch.

Downloaded drawing SHA-256:
`32f1f931c39783bab2b9db34342b438e4a64f63abec095aa3762661d6ae6424b`.

## Physical terminals and schematic contacts

The manufacturer's circuit diagram connects physical terminals **1 and 2**
internally, and **3 and 4** internally. Pressing the button joins those two
groups. The existing KiCad `Switch:SW_Push` symbol has two logical contacts.
Our local footprint therefore repeats each logical pad number on its two
physical terminals:

| Component-side location | GCT terminal | KiCad logical pad |
| --- | --- | --- |
| Upper left (−3.30, −1.50) | 1 | 1 |
| Upper right (+3.30, −1.50) | 2 | 1 |
| Lower left (−3.30, +1.50) | 3 | 2 |
| Lower right (+3.30, +1.50) | 4 | 2 |

Logical pad 1 goes to the corresponding reset/test signal; logical pad 2 goes
to ground. Assigning the two left terminals to one contact and the two right
terminals to the other would be incorrect for this part. The footprint's pad
numbers intentionally differ from the manufacturer's four terminal numbers.

The local library is `Lab4_Switches:GCT_SWT0210_4.5x4.5mm`. The schematic,
individual circuit BOM, purchasing BOM and both assembly views use that same
identifier. No substitution or quantity change was made.

## Verification and limits

`check_placement.py` checks all four pad coordinates, sizes, SMD type and
logical contact pairs for each switch, in addition to their schematic nets,
support clearance and board boundaries. Fresh KiCad ERC/DRC and schematic
parity checks are recorded in `Fabrication-check.json` and `KiCad/Placement-DRC.json`.
All existing part coordinates, rotations and pad nets were preserved when
the switches were added. Each switch is at its former reservation center.

This completes the switch land pattern and contact mapping. It does not
complete routing, button silkscreen/access review or a physical assembly test.
Use the supplier's part drawing to identify the footprint orientation during
assembly; do not treat a different generic four-terminal switch as interchangeable.
