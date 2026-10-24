# October 24 design review package

This package supports the schematic, bill of materials and high-level design
review. It is not a manufacturing release. Detailed PCB layout is due October 29.

| Deliverable | Current source | Review status |
|---|---|---|
| Schematic | KiCad/Lab4.kicad_sch and its four child sheets; Lab4-Circuits.pdf | 284 components / 297 nets; electrical checks pass. Thermal/protection and external interfaces still have explicit open decisions. |
| Parts list | Preliminary-BOM.csv | Circuit plus itemized external/mechanical parts, sources and spares. Tenergy 11609/01025 are zero-quantity references under the October 24 DigiKey/Mouser sourcing rule; no replacement pack/charger is finalized. Fuse, spacers, fasteners, shunts, LEDs and adapter candidates are itemized; sourcing, physical/electrical qualification and heatsink attachment remain open. |
| Course assembly plan | BOM-Hand-assembly.csv; Assembly-options.md | TA confirmed team assembly of all SMD on October 23. Use course v3 stock first; TechSpark oven access is tentative. JLC comparison is historical. |
| High-level design | Shared Lab 4 Writeup; Lab4-System.drawio | Power, three zones, dual CAN, sensing and proposed physical arrangement. Calculations are distinguished from measurements. |
| Verification | Verification.txt, KiCad/ERC.txt, Placement-check.json, KiCad/Placement-DRC.json | Software checks only; no assembled-PCB test. |

## Decisions to close or present explicitly at the review

1. Resolve a battery/charger combination under the October 24
   [DigiKey/Mouser purchasing rule](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792870041277289).
   Tenergy 11609/01025 remains an earlier design reference, not a finalized
   purchase. The team reports that a
   115x50x50mm cardboard stand-in fits between the chassis plates, with
   approximately 51.75mm usable height. Final strap/lead routing and an actual
   pack installation remain; the preliminary envelope check is complete.
2. Reconcile requested quantities with course v3 stock and identify extra
   purchases. The assembly question is answered: the team will assemble the
   board. The purchasing vendors are DigiKey/Mouser outside course stock. The team will send the three review
   deliverables to its small-group TA via Slack.
3. Confirm course expectations for L298 brief-stall protection and the actual
   heatsink mounting arrangement. Keep the course driver; do not call a 3.2 A
   motor stall specification normal current or qualified driver operation.
4. The October 24 servo photos and reported functions, and one motor/encoder
   harness's reported order, are recorded in Actuator-design.md. Identify
   adapter parts and unresolved sourcing/fit in the review. Check the second
   motor harness and actual mating geometry before preparing adapters;
   completed-harness continuity checks occur after assembly, before first power.
   A finished adapter is not an October 24 review deliverable. The encoder
   supply correction is implemented: J82/J83 use the nominal 3.3V logic rail.
   Actual voltage tolerance and signal quality still require validation. Connector
   family/part selection is documented, but physical compatibility is not tested.
5. Complete the four-rail power budget with traceable measured/datasheet values
   and calculations. Label provisional estimates and assumptions explicitly.
   Existing Lab 2 telemetry is not calibrated evidence. The handout explicitly
   requests measured motor stall current and L298 loss/temperature in Part 1.1;
   these remain unfinished. The extra measurement worksheet is a recording aid,
   not an additional course deliverable. Estimates do not complete the explicit
   measurement requirement; acceptance of deferred measurements is up to staff.

We do not represent these open decisions as completed. If an answer is not
available before the review, the report should identify it and request specific
feedback; this document does not establish that the TAs will accept an incomplete
item. Littelfuse0297010.L is a review candidate, not a qualified protection
design: normal/startup current and the complete power path still need checking.

## Work before fabrication

Verify five GCT switch footprints; resolve the heatsink placement conflicts;
confirm the Pi/chassis spacer stack, cable reach and screw/washer clearances;
complete routing, power copper and thermal design; confirm the course
assembly/stencil process; and export/check Gerbers, drill files and final BOM.
Prepare component positions if requested for the final course submission.
The current 499 unconnected items are expected for an unrouted study and are
not acceptable for fabrication.

The shared Google Doc is edited in place. Editable design sources remain in
Git, with linked previews; Drive should not contain competing design copies.
Before sending the review, commit one coherent source revision and identify it
in the submission. No email, Slack post, TA submission or manufacturing order
was made as part of this review.

## Lab 1 revision record

We added Section 11 to the existing [Requirement Document](https://docs.google.com/document/d/182TcM6g2DfyiQt0xGXAkl2lv_5BjBLEOPw9v7Lpieis).
It records the PCB hardware, retained CAN IDs, added sensing and LEDs, and
the required firmware port from Lab 3 PB4 actuator PWM to the Lab 4 PA9/PB7
outputs. The port and real current/speed feedback are not implemented or tested.
The shared [Lab 4 Writeup](https://docs.google.com/document/d/1zMR_S5QoFPES1BhswG5bhpLGAib2P71ri6rK2hKzBcc)
is the high-level brief; its exported revision has four text pages and two
separate figure pages. The dimensioned fit template is a separate supplement.
