# October 24 design review package

This package supports the schematic, bill of materials and high-level design
review. It is not a manufacturing release. Detailed PCB layout is due October 29.

| Deliverable | Current source | Review status |
|---|---|---|
| Schematic | KiCad/Lab4.kicad_sch and its four child sheets; Lab4-Circuits.pdf | 284 components / 297 nets; electrical checks pass. Thermal/protection and external interfaces still have explicit open decisions. |
| Parts list | Preliminary-BOM.csv | Circuit plus itemized external/mechanical parts, sources and spares. Tenergy 11609/01025 selected; Dantona requested quantity is zero. Exact fuse candidate, spacers, fasteners, shunts, LEDs and adapter parts selected; physical/electrical qualification and heatsink attachment remain open. |
| Course assembly plan | BOM-Hand-assembly.csv; Assembly-options.md | TA confirmed team assembly of all SMD on October 23. Use course v3 stock first; TechSpark oven access is tentative. JLC comparison is historical. |
| High-level design | Shared Lab 4 Writeup; Lab4-System.drawio | Power, three zones, dual CAN, sensing and proposed physical arrangement. Calculations are distinguished from measurements. |
| Verification | Verification.txt, KiCad/ERC.txt, Placement-check.json, KiCad/Placement-DRC.json | Software checks only; no assembled-PCB test. |

## Decisions to close or present explicitly at the review

1. Verify mounting, wiring, cost and delivery for the selected Tenergy
   11609/01025 combination. Its documented current rating and charger
   compatibility support the design choice; physical fit is not yet verified.
2. Reconcile requested quantities with course v3 stock and identify extra
   purchases. The assembly question is answered: the team will assemble the
   board. Confirm the purchasing process. The team will send the three review
   deliverables to its small-group TA via Slack.
3. Confirm course expectations for L298 brief-stall protection and the actual
   heatsink mounting arrangement. Keep the course driver; do not call a 3.2 A
   motor stall specification normal current or qualified driver operation.
4. Verify existing cable pin order, mating plugs and wire gauge against the
   selected adapter components in Parts-review.md. Reconcile the motor
   specification's 3.3-5V encoder supply with the schematic's 5.1V connection
   before power is applied; this digital correction remains open. Connector
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
