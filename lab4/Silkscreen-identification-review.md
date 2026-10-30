# October 30 board identification and fabrication handoff

We added **649 Team 4**, **Tianyi He**, **Felipe Marples Rodriguez**, and
**Sida Cheng** to the front silkscreen in the clear area between the rear
mounting holes. This implements [Tom's October 30 request](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793373919768429).
The board name uses 1.8 mm text and the names use 1.1 mm text.

## Fabrication stack to include with the submitted files

- Four copper layers, nominal 1.6 mm board thickness.
- Reference stack: **JLC04161H-7628**.
- Outer copper: **1 oz**, nominal 35 micrometres.
- Inner copper: **0.5 oz**, nominal 15.2 micrometres.
- Layer order: F.Cu / In1.Cu / In2.Cu / B.Cu.
- No 2 oz copper or controlled-impedance order is requested.

These values match the saved PCB and [layer-stack record](Layer-stack.md).
[Professor Rowe's October 30 message](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793374847869419)
asks teams to identify special stack requirements. We included the explicit
stack in the package's `REVIEW-ONLY.txt`; we have not sent it to staff or placed
an order. Staff review and the course submission remain separate actions.

## Scope of the change

Only four silkscreen text objects were added. Removing those exact objects
reproduces the previous PCB bytes; components, copper, drill geometry, outline,
rules and stack are unchanged. [The comparison record](Silkscreen-identification-check.json)
identifies both board hashes and the prior commit. Earlier power and mechanical
calculations retain their original source hashes and still apply to this
unchanged geometry. They were not represented as new calculations.

Fresh native ERC/DRC, schematic parity and connectivity checks and regenerated
manufacturing exports accompany this revision. We visually checked the new
identification text. This is a prototype review package, not a fabrication
release or a powered hardware test.
