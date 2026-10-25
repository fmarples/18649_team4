# Lab 4 fabrication review

The October 24 preliminary submission and the October 29 fabrication submission
are different releases. We emailed the preliminary schematic, purchasing BOM,
report and fit template on October 24. The current PCB is **not ready for fabrication**.
The [handout](https://drive.google.com/file/d/1BY2rbBwuB3GaSkNRFC7Hki2tzdnRCmCk/view)
requires the final files on Gradescope by **October 29, 2026, 11:59 p.m.**
The class fabrication batch follows the next morning.

## Current evidence

The October 25 checks use the CAD at `c7ef66d` with five PCB datasheet fields
synchronized to their schematic values (R540 and R800-R803). No pad, net,
placement or routing changed. The fresh schematic export has
284 components and 297 nets. ERC reports no findings under the configured rules;
the existing connectivity/BOM and placement checks pass. These checks do not
establish component ratings or completed routing. The board has 279 electrical
footprints, eight supports, no routed tracks and no copper zones. Five switches
are absent: SW50, SW51, SW60, SW61 and SW70.

`Fabrication-check.json` records the fresh fabrication audit, its source hashes,
missing parts, DRC results and ignored rule categories. It deliberately reports
the board as blocked. A placement-only pass must not be used as a release result.

## Decisions needed before the layout is fixed

| Decision | Evidence needed | Why it affects fabrication |
| --- | --- | --- |
| Battery and charger | Exact pack, continuous current and any pulse rating with duration, full-charge and discharged voltage bounds, dimensions, connector/polarity and compatible charger from a permitted source | Determines input voltage/current, connector, fuse, wiring and mechanical space. The provisional Amazon pack is not qualified: its published 2 A continuous rating does not cover the assumed 2.883 A planning case; no 10 A pulse rating was established. |
| Motor protection and fuse | TA/course expectations for fault handling; chosen fuse time-current behavior versus wiring, connectors, holder and load/startup envelope | A 10 A input fuse is not fast protection for an individual L298 bridge. A circuit change must happen before routing. The raw 3.2 A motor stall figure is not an allowed continuous L298 operating point. |
| L298 and 6396BG installation | Attachment orientation, height and any PCB mounting holes/insulation | The tentative heatsink rectangle intersects 15 other courtyards. Acceptance of the heatsink part for the preliminary review did not verify this installation. Resolve the envelope before moving nearby parts. See `Heatsink-envelope-check.json`. |
| Pi and chassis stack | Actual Pi/socket/cooler/ports and screw-tail fit; selected spacers; full steering travel; reachable headers; course interpretation of the Pi mounting margin | Four-hole paper alignment was checked at approximately 50 mm chassis spacing. The model proposes 35 mm chassis spacing and a 22 mm Pi gap; these are not physically verified. Pi holes use a 3 mm radius from the center, not 3 mm from the drilled edge. |
| Cable interfaces and stock | Confirm second motor harness, servo mating part/current capability and supplied quantities; choose permitted replacements if unavailable | A different PCB connector or part package changes pads and placement. Adapter continuity/temperature tests happen after assembly; the intended mating interface and rating basis must be established first. |

Aim to resolve decisions that change CAD by Monday, October 26. This is a team
planning target, not a separate course deadline. If an answer is unavailable,
obtain an explicit TA-approved design/deferral; do not infer that an October 24
review allowance authorizes fabrication of an unresolved circuit.

For the motor-stall and L298 drop/temperature questions, the recorded TA deferral
only establishes that measurements were not needed on October 24. Confirm what
the final brief should contain on October 29. Published values and calculations
must stay labeled as such. Do not perform a prolonged stall through the L298 to
produce a missing number.

## Footprints and routing

The GCT [SWT0210 manufacturer drawing hosted by Mouser](https://www.mouser.com/catalog/specsheets/GCT_05-30-2025_SWT0210%20Product%20Drawing.pdf)
identifies the recommended land pattern and contact diagram. Verify the actual
drawing, including which physical terminals are internally connected, before
creating the local footprint and mapping the two-pin schematic switch onto it.
The October 25 text retrieval located the drawing, but local downloads returned
HTML and the available screenshot tool did not return viewable pixels. The five
footprints have therefore not been assigned from an inferred pin arrangement.

After the mechanical and electrical decisions are settled:

1. Assign all footprints and check pin 1, pad numbering, pitch, package/body
   dimensions, polarity, drill sizes and courtyard. Update the schematic and all
   three BOM views together. Keep course part numbers unless a replacement has
   been checked. Place the real switches, replacing their drawing reservations.
2. Resolve the heatsink conflict and tighten the power-stage placement according
   to the [TPS564252 layout guidance](https://www.ti.com/lit/ds/symlink/tps564252.pdf).
   Keep the input switching loop short and feedback away from the switch node.
   Place bypass capacitors next to their IC supply pins and crystals next to
   the MCP2515s. The current board is a placement study, not a validated power layout.
3. Route the battery, motor and regulator current paths with calculated copper
   widths/pours and returns. The handout's 0.50 mm power minimum is not a current
   rating. Route servo-shunt sense traces as a Kelvin pair so load-current copper
   drops are not included in the measurement.
4. Route separate linear CAN A/B backbones with H/L paired, ground reference
   beneath them, and terminators on the bus side of isolation jumpers. Keep the
   two buses separated from one another and from motor/switching copper. Route
   local SPI, clocks, ADC and remaining signals, then fill the ground plane.
5. Add usable silkscreen: connector pins/polarity, zone/bus, isolation/termination,
   test signals, buttons and SWD pin 1. Check reachability with the assembled
   stack, not just an unobstructed top-down drawing. Recheck the final 1:1 print
   when outline, hole centers or occupied envelopes change.

## Run the checks on the finished board

Use KiCad's normal ERC/DRC dialogs while editing. For a repeatable audit, use
KiCad's bundled Python (which supplies `pcbnew`) and an empty output directory:

```text
python check_fabrication.py --kicad-cli /path/to/kicad-cli --output-dir /path/to/new-check-directory
```

The audit exports a fresh netlist, runs ERC, then runs DRC with schematic parity
and refilled zones. Parity means that board components and connections agree
with the schematic. It does not save over the PCB. It refuses to reuse an old
report directory, records source hashes, and returns a nonzero exit code for
missing footprints, unrouted connections or reported findings. Inspect ignored
rule categories and warnings; do not suppress real violations to get a pass.

Run the existing `check_netlist.py` against the audit's `netlist.xml` to compare
the circuit and purchasing/assembly BOMs. `check_placement.py` is specifically
for the existing unrouted study; its zero-track assertion is not a final-board
check. A final review must also check actual routing, return paths, thermal
space, high-current copper and manufacturing files. Automated checks cannot
replace those engineering judgments or the TA review.

## Required final package

All files must describe the same reviewed source revision:

- Design brief, at most four pages excluding figures/chassis drawing: final
  power budget and battery justification, measured geometry and outline,
  three current-sensing circuits, part choices, and remaining honest limitations.
  Edit the existing [shared report](https://docs.google.com/document/d/1zMR_S5QoFPES1BhswG5bhpLGAib2P71ri6rK2hKzBcc/edit).
- Schematic PDF, one page per block, with named nets, value/footprint/part fields,
  and clean ERC; reconcile every R1/R2.5/R3/R4.1-R4.8/R5/R6/R7 and Lab 3 test-point
  requirement against the final schematic and layout.
- PDF of each PCB layer plus a 3D render or final 1:1 print-on-chassis photo.
- Gerber and drill ZIP, stated layer count, and zero-error DRC report. Inspect
  the generated layers and drills in a Gerber viewer before submission.
- JLC-format BOM and CPL (component position list), plus course-shelf quantities.
  Include component reference, value, footprint, exact MPN and assembly status;
  use verified LCSC IDs/Basic-or-Extended categories where available. The
  [October 24 clarification](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792874096905749)
  says to add LCSC numbers where feasible and plan around the course parts.
  [October 25 follow-up](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792945784851839)
  allows the described N/A/hand-assembly approach for unavailable library parts.
  Do not substitute parts solely to fill a catalog column. No explicit waiver of
  the handout's CPL requirement was found. The historical JLC comparison is not
  a ready assembly-order BOM.
- Update the existing Lab 1 revision-history entry to match final pin, LED and
  message-catalog changes. Do not claim unimplemented firmware changes work.
- Record the TA's blocking-issue closure and submit the final package to
  Gradescope. The preliminary email is not this final submission.

Target final exports and a second-person review for Wednesday, October 28, with
Thursday reserved for TA corrections and upload checks. Assembly, powered
bring-up, adapter continuity and thermal/load tests on the new board occur after
boards arrive; they must remain marked unperformed in this submission.
