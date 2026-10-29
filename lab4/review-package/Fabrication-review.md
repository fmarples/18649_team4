# Lab 4 fabrication review

The October 24 preliminary submission and the October 29 fabrication submission
are different releases. We emailed the preliminary schematic, purchasing BOM,
report and fit template on October 24. The current PCB is **not ready for fabrication**.
The [handout](https://drive.google.com/file/d/1BY2rbBwuB3GaSkNRFC7Hki2tzdnRCmCk/view)
requires the final files on Gradescope by **October 29, 2026, 11:59 p.m.**
The class fabrication batch follows the next morning.

## October 28 capacitor and chassis allowance revision

The latest [power-route/package correction](Power-route-revision.md) widens
779 power segments and fixes C802 to D10/P5. The detailed physical stack is
saved in the PCB. Native ERC/DRC/parity/connectivity and 331 targeted routes
pass; 41 critical components have package checks. A matching
[review package](review-package/REVIEW-ONLY.txt) is exported and independently
parsed: 11 Gerber layers, 1,330 plated holes, 12 nonplated holes and 300
electrical position rows. Layer PDFs are scaled to fit; the separate
Placement-fit-template.pdf is the 1:1 template. Custom parts without 3D models
are omitted from the native renders, so those views do not prove full fit.

The Gerber parser notes KiCad's G90 placement and unused RoundRect macro
parameters; neither prevented parsing. Every exported drill position/diameter
matches the saved board within the 0.001 mm file precision. Both outer
Gerber composites and the four copper PDF pages were inspected. Final
fabrication release is still withheld for the operating-power and protection
decisions, followed by the resulting final engineering review.

The review BOM/CPL use JLC column names and retain the course hand-assembly
status. Missing catalog numbers are N/A, not guessed. Native KiCad rotations
are only normalized modulo 360; they are not assembly-library rotation
corrections. No PCBA upload or order is implied.
[JLC BOM columns](https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly),
[JLC position columns](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly).

We selected rear chassis pair A1/A2 after the team confirmed both holes are
unused and accessible. CAD dimensions are 47.870 mm front, 73.01493 mm rear
and 233.21155 mm between rows; team measurements are about 48, 73.45 and
232.85 mm respectively. The PCB is now 120 × 247.21155 mm, extended
13.21155 mm rearward. H1–H4 use 4.0 mm NPTH holes for M3 with 4 mm edge
exclusions; Pi supports remain 2.7 mm with 3 mm exclusions. The earlier
cardboard test used the previous pattern. See
[Mounting-tolerance-revision.md](Mounting-tolerance-revision.md).

We replaced the six small buck-output capacitors and added ten parallel
capacitors. Each input bank is now 66 µF nominal; servo/Pi/logic output banks
are 88/66/66 µF. The selected 1210 parts and 68/91/30 pF feed-forward values
are documented in [Capacitor-bank-review.md](Capacitor-bank-review.md).
The bias/tolerance/temperature/aging screen passes the stated capacitance
targets. This is a calculated design screen, not measured transient or
thermal qualification.

## October 27 mounting and encoder revision

We implemented the 3 mm clearance from the **finished hole edge** at all
four chassis and four Pi support holes. The exclusions cover components,
tracks, vias and filled copper on all four layers. The Pi socket is now
**Samtec ESQ-118-44-L-D**, mating physical Pi pins **3–38**. The first socket
pair must align with Pi pins 3/4, not 1/2. Pin 4 alone supplies 5 V. All used
signals and Lab 3 assignments are unchanged. Do not substitute the old
40-contact socket: it violates the hole-edge clearance.

We also installed the 6396BG anchor footprint, moved U80/C800/C802/J80,
and repaired local routing. A new 4.0 V encoder rail replaces the marginal
3.3 V encoder feed; the signal buffer and its pull-ups remain at 3.3 V.
See [Mounting-and-encoder-revision.md](Mounting-and-encoder-revision.md)
for exact parts, calculations, checks and remaining limitations.

The current board has 300 electrical footprints plus eight supports and
HS80, 20,264 track/via items and six filled ground zones. The targeted routing
check covers 331 connections. Fresh native findings and source hashes are in
[Fabrication-check.json](Fabrication-check.json). These checks do not authorize
fabrication. Pi voltage margin, motor/fuse protection, application cutoff
integration and final purchasing/manufacturing review remain. The capacitor
selection and routing revision is implemented; loop/transient and thermal
behavior still require qualified review and later prototype validation.


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

We selected rear chassis pair A1/A2 after the team confirmed both holes are
unused and accessible. CAD dimensions are 47.870 mm front, 73.01493 mm rear
and 233.21155 mm between rows; team measurements are about 48, 73.45 and
232.85 mm respectively. The PCB is now 120 × 247.21155 mm, extended
13.21155 mm rearward. H1–H4 use 4.0 mm NPTH holes for M3 with 4 mm edge
exclusions; Pi supports remain 2.7 mm with 3 mm exclusions. The earlier
cardboard test used the previous pattern. See
[Mounting-tolerance-revision.md](Mounting-tolerance-revision.md).

| Decision | Evidence needed | Why it affects fabrication |
| --- | --- | --- |
| LiPo implementation | Approved CNHL S220403BK / Hitec 44295 pair, added PA3 divider and tested standalone guard; complete application integration and harness/fuse review | Selection is complete. The advertised pack capability does not authorize motor stalls. Cutoff demonstration and actual connector polarity/retention checks must precede LiPo operation. |
| Motor protection and fuse | TA/course expectations for fault handling; chosen fuse time-current behavior versus wiring, connectors, holder and load/startup envelope | A 10 A input fuse is not fast protection for an individual L298 bridge. A circuit change must happen before routing. The raw 3.2 A motor stall figure is not an allowed continuous L298 operating point. |
| L298 cooling/fault envelope | Mounting geometry is implemented and checked; finalize allowable motor current/duty and fault handling | The heatsink footprint and routing no longer await a measurement. Thermal qualification still depends on the operating envelope. |
| Pi and chassis stack | Completed drawing-based review: 35 mm chassis / 22 mm Pi gap; all eight supports satisfy the 3 mm hole-edge rule | ESQ-118-44-L-D clears the Pi hole edge by 4.535 mm. Keep accessories and hardware within documented envelopes; actual mating/retention/steering are assembly checks. No rule exception is pending. |
| Cable interfaces and stock | Select a servo mating part with documented current capability and confirm supplied quantities; choose permitted replacements if unavailable | A different PCB connector or package changes pads and placement. The second motor harness, adapter fit/continuity and temperature are checked during assembly; they do not require a new photo task now. The intended mating interface and rating basis must still be established before release. |

Resolve decisions that change CAD now, before the Wednesday final-export target. This is a team
planning target, not a separate course deadline. If an answer is unavailable,
obtain an explicit TA-approved design/deferral; do not infer that an October 24
review allowance authorizes fabrication of an unresolved circuit.

The motor-stall, L298 drop/temperature and servo-holding prompts appear under
**Guiding Questions** in Lab 4 (pp. 3–4). The required final brief is specified
separately on pp. 11–12. We will provide the required power budget and explain
the sources and assumptions; a new measurement campaign or blanket measurement
waiver is not a release prerequisite solely because of those guiding questions.
Lab 2 p. 5 also explicitly distinguishes guiding questions from graded
deliverables. This is a reading of the handouts, not a new TA waiver. Any
specific subsequent TA requirement still applies. Source research and planning
estimates are complete; the board's actual voltage, temperature and fault
behavior remain untested. Electrical design limits still need to be justified.

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

1. Resolve the input-power/protection and operating-load decisions above, then update
   only their affected schematic, placement and routes.
2. Close the remaining component and power-margin findings in
   [Digital-review.md](Digital-review.md):
   Pi/logic feed and return refinement, the implemented capacitor-bank/control-loop review
   and cooling assessment. The analytical screens
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

The October 28 capacitor revision addresses the earlier capacitance shortfall
with larger parallel banks and documented feed-forward choices. See
[Capacitor-bank-review.md](Capacitor-bank-review.md). Final engineering review
and startup/load-step/temperature validation must not be inferred from DRC.
