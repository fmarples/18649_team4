# Lab 4 fabrication review

## Current status

The files are ready for the course's final **prototype fabrication review**.
We recommend retaining the present CAD for that review. This is not a claim
of TA acceptance, an order authorization, or completed electrical qualification.
The [October 29 extension](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793301588360959)
sets the deadline to **Saturday October 31, 2026, 10:00 p.m.** Staff will check
boards before the fabrication batch. The October 24 preliminary email is a
different submission.

The [load-specific operating review](Prototype-operating-review.md) closes the
remaining digital planning work for a bare Pi running the car software. It
uses 1.5 A Pi + 0.3 A other 5 V loads, with clearly labeled assumptions and a
2 A Pi sensitivity. Sustained 3 A Pi qualification, extra peripherals and
optional hardware current limiting are deferred. They are not hidden release
requirements. We have not powered the new PCB or guaranteed its behavior.

## Matching CAD and manufacturing checks

The board has four copper layers on the documented 1.6 mm
[JLC04161H-7628 stack](Layer-stack.md). There are 300 electrical footprints,
eight supports and HS80, 20,264 track/via items and six ground zones. Native
ERC/DRC, schematic parity and unconnected counts are zero. There are 331
targeted connection checks and 282 components in the package audit.

The October 30 CAD change adds the board name **649 Team 4** and all three
team members' names to the front silkscreen. Copper, components, holes, outline
and stack are unchanged; see the [identification and stack handoff](Silkscreen-identification-review.md)
and its exact previous/current-board comparison. Earlier electrical calculation
records retain their original hashes and still apply to that unchanged geometry.

The preceding CAD change gave U80's 15 plated pins 1.1 mm finished holes,
without changing their centers, 1.8 mm pads or heatsink anchors. Matching
exports contain 11 Gerber layers, 1,330 plated and 12 nonplated holes and
300 position rows. Independently parsed drill locations/diameters match the
saved board within 0.001 mm. Outer composites and copper-layer PDFs were
visually reviewed. The identification revision regenerates the matching
manufacturing exports and native checks.

Front/rear hole spacing is 47.870/73.01493 mm, row separation 233.21155 mm;
board outline is 120 × 247.21155 mm. H1–H4 are 4.0 mm NPTH for M3, with
4 mm hole-edge exclusions. Pi holes are 2.7 mm with 3 mm exclusions. Team
measurements support the selected CAD pair; no repeat measurement is pending.
See [mounting](Mounting-tolerance-revision.md) and
[Pi/heatsink geometry](Mounting-and-encoder-revision.md).

The 36-contact ESQ socket mates Pi physical pins 3–38, with 5 V on pin 4.
Do not substitute the old 40-contact socket. The shortened part preserves
the required hole clearance. Its assembly process and physical seating are
post-fabrication checks, not a missing geometry decision.

The [capacitor-bank review](Capacitor-bank-review.md),
[return-path review](Return-path-review.md), and
[prototype power calculations](Prototype-power-check.json) document the
remaining analytical limitations. The estimated normal input is 2.19–2.50 A;
the 5.63–6.49 A sensitivity is not a continuous rating. Main input fuse/harness
selection and actual operating behavior must be validated before LiPo use.
The removable fuse and external servo lead do not require a PCB footprint
change. A higher continuous load or different connector would reopen CAD review.

## Required work by stage

**Before fabrication:** team/TA review of this matching package, including
the operating assumptions and conditional input fuse, followed by any necessary
correction and the course submission. The team should flag the normal-use
assumptions directly, rather than asking for blanket approval of a 3 A stress case.

**Before ordering/assembly:** confirm actual course-stock shortfalls and exact
seller/variant; resolve the servo lead; plan local soldering for the Samtec
socket and suitable paste deposition for the inductors/fine-pitch ICs. BOM
exceptions stay visible. These are not completed purchasing or assembly actions.

**Before battery-powered driving:** inspect and commission from a current-limited
bench supply, test actual Pi startup/car workload and temperatures, qualify the
installed harness/fuse, and integrate/test the battery guard. The full sequence
is in [Prototype-operating-review.md](Prototype-operating-review.md).

**Optional/deferred:** sustained 3 A Pi or high aggregate current operation,
added accessories, deliberate stall characterization, extra hardware limiting,
2 oz copper conversion and expanded proprietary simulation. None is needed
to prepare the selected prototype for course fabrication review.

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
- Gerber and drill ZIP, stated layer count, and zero-error DRC report. State
  **4 layers, 1.6 mm, JLC04161H-7628, 1 oz outer / 0.5 oz inner copper** in
  the fabrication handoff; no 2 oz or controlled-impedance order is requested. Inspect
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
- Submit the reviewed package to Gradescope and retain the receipt. The
  preliminary email is not this final submission. Record any TA changes from
  the course pre-fabrication review before the order is released.


## Recheck only affected work

The current package sources and output hashes are recorded in
[review-package/manifest.json](review-package/manifest.json). After a CAD change,
run `check_fabrication.py` with KiCad Python, the KiCad CLI and a fresh output
directory; rerun affected mechanical, netlist, routing and power checks, then
regenerate/inspect the changed exports. Do not suppress real errors to get a pass.
The analytical scripts' `fabrication_release: false` fields mean that a
calculation does not authorize fabrication. The package remains marked review
until the course/team release step; no order or submission has been performed.
