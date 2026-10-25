# October 24 design review package

This package supports the schematic, bill of materials and high-level design
review. It is not a manufacturing release. Detailed PCB layout is due October 29.

| Deliverable | Current source | Review status |
|---|---|---|
| Schematic | KiCad/Lab4.kicad_sch and its four child sheets; Lab4-Circuits.pdf | 284 components / 297 nets; electrical checks pass. Thermal/protection and external interfaces still have explicit open decisions. |
| Parts list | Preliminary-BOM.csv | Circuit plus itemized external/mechanical parts, sources and spares. Tenergy Amazon B077Y9HNTF is a provisional battery candidate: its published 2A continuous limit is below our 2.883A planning case, and 10A pulse capability and fit are unverified. Charger and servo-side lead remain unresolved. All new non-battery purchases require DigiKey/Mouser. Tenergy 11609/01025 remain zero-quantity references. Anson accepted 6396BG for review; attachment is a deferred staff follow-up. |
| Course assembly plan | BOM-Hand-assembly.csv; Assembly-options.md | TA confirmed team assembly of all SMD on October 23. Use course v3 stock first; TechSpark oven access is tentative. JLC comparison is historical. |
| High-level design | Shared Lab 4 Writeup; Lab4-System.drawio | Power, three zones, dual CAN, sensing and proposed physical arrangement. Calculations are distinguished from measurements. |
| Verification | Verification.txt, KiCad/ERC.txt, Placement-check.json, KiCad/Placement-DRC.json | Software checks only; no assembled-PCB test. |

## Decisions to close or present explicitly at the review

1. Present the provisional battery/charger design and unresolved procurement under the October 24
   [purchasing rule](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792870041277289)
   and its [battery-only Amazon exception](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792878299024869).
   The BOM identifies [Tenergy Amazon B077Y9HNTF](https://www.amazon.com/dp/B077Y9HNTF)
   as one provisional review candidate. Its published 2A continuous limit is
   below the assumed 2.883A battery-input case; no 10A pulse rating/duration
   was found. It is not qualified for operation or purchase. Check Pittsburgh
   delivery and a compatible charger; charger sourcing is not covered by the
   Amazon exception.
   Ayaan's October 24 evening DM permits tonight's review to use the provisional
   design and identify a replacement for the following week. Anson allows
   somewhat longer delivery. Tenergy 11609/01025 remains a design reference,
   not a finalized purchase. All new non-battery purchases, including the
   charger, must use DigiKey/Mouser. The team reports that a
   115x50x50mm cardboard stand-in fits between the chassis plates, with
   approximately 51.75mm usable height. The candidate's 73.5x53.5x30.5mm
   dimensions are outside that checked envelope, so a different mounting
   arrangement needs checking. Final strap/lead routing and an actual pack
   installation remain; the preliminary envelope check is complete.
2. Reconcile requested quantities with course v3 stock and identify extra
   purchases. The assembly question is answered: the team will assemble the
   board. Use DigiKey/Mouser outside course stock, with the battery-only Amazon
   exception described above. The supplier check in Parts-review.md separates
   permitted purchase links, course-stock requests, and unresolved items.
   Preliminary-BOM.csv now has a `TA_review` column asking for course-stock
   allocations and a suitable servo lead. U81 sourcing is resolved with the
   reviewed SN74LVC14APW tube-pack alternative from DigiKey: two individual
   ICs total, with no circuit or footprint change. Recheck stock at purchase.
   The team will send the three review
   deliverables to its small-group TA via Slack.
3. Record any clarification of expected L298 brief-stall/protection behavior,
   or flag it as an open engineering question. The October 24 team reply relays
   that Anson accepted 6396BG and will investigate its mounting hardware; the
   shared checklist records that attachment is not needed for today's review.
   Do not require the team to select a mounting kit tonight. This acceptance
   does not establish a safe stall duration or a per-motor current limiter.
4. The October 24 servo photos and reported functions, and one motor/encoder
   harness's reported order, are recorded in Actuator-design.md. Identify
   adapter parts and unresolved sourcing/fit in the review. Check the second
   motor harness and actual mating geometry before preparing adapters;
   completed-harness continuity checks occur after assembly, before first power.
   A finished adapter is not an October 24 review deliverable. The encoder
   supply correction is implemented: J82/J83 use the nominal 3.3V logic rail.
   Actual voltage tolerance and signal quality still require validation. Connector
   family/part selection is documented, but physical compatibility is not tested.
5. Use the completed four-rail planning case with its sources and explicit
   assumptions. The team relays Anson's confirmation that measured motor stall
   current and L298 loss/temperature are not needed for October 24; the shared
   checklist also records that the listed measurements can wait. State that
   they are deferred and unmeasured, not completed. Existing Lab 2 telemetry is
   not calibrated evidence. The extra worksheet remains an optional recording aid.

We do not represent these open decisions as completed. If an answer is not
available before the review, the report should identify it and request specific
feedback. The measurement and heatsink-attachment deferrals above have now
been reported by the team; other unanswered items are not implicitly accepted.
Littelfuse0297010.L is a review candidate, not a qualified protection
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
