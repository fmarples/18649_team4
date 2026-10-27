# Lab 4 fabrication review

The October 24 preliminary submission and the October 29 fabrication submission
are different releases. We emailed the preliminary schematic, purchasing BOM,
report and fit template on October 24. The current PCB is **not ready for fabrication**.
The [handout](https://drive.google.com/file/d/1BY2rbBwuB3GaSkNRFC7Hki2tzdnRCmCk/view)
requires the final files on Gradescope by **October 29, 2026, 11:59 p.m.**
The class fabrication batch follows the next morning.

## Current evidence

The October 25 updates add the five GCT switch footprints using the verified
manufacturer A1 drawing and refine the three regulator groups. All 284 schematic components now have matching PCB
footprints, with eight additional mechanical supports and 298 schematic nets.
The switch contact pairs, pad dimensions and nets pass the placement checks;
the circuit and three BOM views agree. The regulator revision moves/rotates
30 footprints while preserving their pad nets and all unrelated positions.
The regulator pin/divider review is recorded in [Power-stage-review.md](Power-stage-review.md).
The current routing contains 16,605 track segments, 973 vias and six
ground zones on four copper layers. All 306 targeted connection checks pass.
Fresh ERC, native PCB DRC and schematic parity have zero findings; native
DRC and the full connectivity count both report zero missing connections.
The schematic separates the two unused Pi 3.3 V pins into individual
no-connect nets. All 284 electrical footprints and eight supports match.
See [Routing-review.md](Routing-review.md) for the signal and power changes.
The latest [digital review](Digital-review.md) records shared-trunk current
allocation, the latest 768 wider logic and 541 wider five-volt segments,
precision feedback resistors,
CAN branches/detours, separate sense taps and functional labels. All 32
near-opening via sites were moved; the 0.15 mm nominal screen is now clear.
These checks do not establish ground-return voltage loss, effective capacitor
bias behavior or board temperature. The source/BOM resistor changes must also
be reconciled with the October 26 purchasing snapshot.
The subsequent [power-margin review](Power-margin-review.md) completes voltage,
capacitor/feed-forward and thermal sensitivity calculations. Its voltage
results now include the wider supply copper. It identifies an encoder
supply-range question and limited Pi margin;
component-data and design closure remain necessary.

`Fabrication-check.json` records an automated PASS with source hashes and
ignored rule categories. This establishes the checked CAD connections and
rules, not current/thermal ratings, physical fit or release approval. The
engineering decisions and export/review tasks below still block fabrication.

## October 26 course updates

Staff [explicitly allow four-layer PCBs](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793033728122419).
The saved PCB now has an internal ground plane on In1.Cu and signal routes on
In2.Cu, with the mounting/antenna keep-outs extended to both inner layers. The
nominal board thickness remains 1.6 mm. No controlled impedance is claimed.
The [JLC04161H-7628 reference stack](Layer-stack.md) is documented. The initial
[return-path review](Return-path-review.md) separates verified connections from
the remaining noise/current geometry checks. This work needs no new hardware
measurements. Final physical stack,
copper weights, clearances and Gerber layer set must agree before fabrication.

Staff [do not expect board-house assembly; plan to use a stencil](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793033592291259).
Our course hand-assembly plan remains appropriate. Preserve the final BOM/CPL
deliverables unless the course explicitly waives them; the assembly clarification
does not itself waive submission files. Confirm paste layers and stencil apertures
with the final footprint review. The separate CAN A/B test points are already
included, matching the [October 25 clarification](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792901698439919).

## Decisions needed before the layout is fixed

| Decision | Evidence needed | Why it affects fabrication |
| --- | --- | --- |
| Battery and charger | Exact pack, continuous current and any pulse rating with duration, full-charge and discharged voltage bounds, dimensions, connector/polarity and compatible charger from a permitted source | Determines input voltage/current, connector, fuse, wiring and mechanical space. The provisional Amazon pack is not qualified: its published 2 A continuous rating does not cover the assumed 2.883 A planning case; no 10 A pulse rating was established. |
| Motor protection and fuse | TA/course expectations for fault handling; chosen fuse time-current behavior versus wiring, connectors, holder and load/startup envelope | A 10 A input fuse is not fast protection for an individual L298 bridge. A circuit change must happen before routing. The raw 3.2 A motor stall figure is not an allowed continuous L298 operating point. |
| L298 and 6396BG installation | Attachment orientation, height and any PCB mounting holes/insulation | The tentative heatsink rectangle intersects 15 other courtyards. Acceptance of the heatsink part for the preliminary review did not verify this installation. Resolve the envelope before moving nearby parts. See `Heatsink-envelope-check.json`. |
| Pi and chassis stack | Review only remaining layout-dependent cable/port/steering/cooler envelopes and the course interpretation of the Pi mounting margin | Four-hole paper alignment and actual Pi caliper heights are complete. We retain nominal 35 mm chassis and 22 mm Pi spacing, supported by Mechanical-evidence.md. Actual socket mating/fastener retention are assembly checks. Pi holes use a 3 mm radius from the center, not 3 mm from the drilled edge. |
| Cable interfaces and stock | Confirm second motor harness, servo mating part/current capability and supplied quantities; choose permitted replacements if unavailable | A different PCB connector or part package changes pads and placement. Adapter continuity/temperature tests happen after assembly; the intended mating interface and rating basis must be established first. |

Resolve decisions that change CAD now, before the Wednesday final-export target. This is a team
planning target, not a separate course deadline. If an answer is unavailable,
obtain an explicit TA-approved design/deferral; do not infer that an October 24
review allowance authorizes fabrication of an unresolved circuit.

For the motor-stall and L298 drop/temperature questions, the recorded TA deferral
only establishes that measurements were not needed on October 24. Confirm what
the final brief should contain on October 29. Published values and calculations
must stay labeled as such. The question is whether that allowance covers the
final brief, not a request to repeat every possible current measurement. Servo
no-load source research and four-rail planning estimates are already done.
Do not perform a prolonged stall through the L298 to produce a missing number.

The final design can use stated load scenarios and calculated dimensional
margins. Physical tests of the unbuilt board are not prerequisites for
generating fabrication files. Connector mating/continuity, loaded voltage,
noise, thermal behavior and retention are checked at assembly/bring-up. Before
fabrication, resolve uncertainties that could change the circuit, pads,
outline or reserved space. An undocumented battery/connector rating cannot
be created by an estimate. See Current-evidence.md and Mechanical-evidence.md.

## Footprints and routing

The five GCT footprints and their contact mapping are complete. We inspected
the manufacturer's A1 drawing and used its 1.4 mm square lands. Physical
terminals 1/2 share logical pad 1; terminals 3/4 share logical pad 2. See
[Switch-footprint-review.md](Switch-footprint-review.md) for geometry, source
and checks. Functional silkscreen review is complete for the present placement;
recheck button access if the heatsink or neighboring placement changes.

The required electrical connections are routed. Do not treat the completed
signal-routing and label work as pending. Before release:

1. Resolve the input-power/protection and heatsink decisions above, then update
   only their affected schematic, placement and routes.
2. Close the remaining component and power-margin findings in
   [Digital-review.md](Digital-review.md): encoder supply qualification,
   Pi/logic feed and return refinement, exact input/output capacitance data,
   final feed-forward choice and cooling assessment. The analytical screens
   in [Power-margin-review.md](Power-margin-review.md) are complete; they are
   not evidence that the outstanding margins have passed.
3. Recheck any changed footprint, connector, stencil aperture or mechanical
   envelope. The existing mask/paste plots were inspected, but final Gerber,
   drill and stencil exports must follow the final design revision.
4. Have the team review the CAD, access to controls/connectors and the final
   fabrication stack. Repeat only physical checks affected by changed geometry.

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
the circuit and purchasing/assembly BOMs. `check_placement.py` checks placement
and mechanical geometry; `check_routing.py` checks the initial regulator copper
connections. A final review must also check actual routing, return paths, thermal
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
