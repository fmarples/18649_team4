# October 29 course decisions

These updates change the requirement record; they do not establish that an
unbuilt board has passed electrical or mechanical tests.

| Topic | Staff decision | Effect on our design |
| --- | --- | --- |
| L298 hardware overcurrent protection | [Tom, 11:58 EDT](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793289494772009): additional hardware protection is optional. | The course-requirement question is closed. No additional limiter has been implemented. Our current/fuse/thermal engineering assessment is separate; this reply does not qualify sustained stalls. |
| Chassis holes | [Ayaan, 11:22 EDT](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793287370096119): a rigid, functional mounting is required; no particular hole set is graded. | Keep our selected front/A1–A2 pattern and allowances. No new hole-choice approval or repeat measurements are requested. Final retention and fit remain assembly checks. |
| Copper weight | [Anthony Rowe, 03:22 EDT](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793258547439569): 1 oz is normal; staff can specify 2 oz if notified. | The saved stack remains 1 oz outer / 0.5 oz inner. A 2 oz option requires layout/rule/stack review and matching fabrication instructions; it has not been requested or ordered. |
| Power source | [Tom, 11:43 EDT](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793288592357949): the power tree starts at the battery, including the Pi. | Already matches our battery-fed buck architecture. |
| Optional camera | [Ayaan, 12:19 EDT](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793290742831139) and [current clarification](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793290848935289): optional two-pin JST 5 V/GND, 250–500 mA from the global rail, not a Pi/MCU output. | Not part of the required design or present power allocation. No connector or purchase has been added. Adding it would raise our 3.3 A rail allocation to 3.55–3.8 A and require renewed voltage/thermal review and an exact mating connector. |
| Battery/charger | Anson's latest DM remains [October 28, 17:34 EDT](https://18449-f26.slack.com/archives/D0C53Q3DN9X/p1793223291984229): update the BOM for the approved CNHL/Hitec pair. | The active purchasing BOM already contains that pair. The battery's XT60 does not replace the PCB's Hirose interface; the vehicle adapter and two motor adapters remain. |

## Deadline extension — 15:19 EDT

[Ayaan's announcement](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793301588360959)
extends PCB Lab submission to Saturday, October 31 at 10 p.m. Staff plan a
quick review Sunday/Monday before sending the fabrication batch. This
supersedes the original October 29 deadline; it is not an electrical approval.

## Why 2 oz is not an order-setting-only change

[JLCPCB's current copper-weight guide](https://jlcpcb.com/help/article/jlcpcb-copper-weight)
lists 0.16 mm minimum trace/space for 2 oz copper. Our regulator land pattern
currently uses a local 0.15 mm gap exception. Therefore the existing DRC pass
does not certify the layout for 2 oz fabrication. Even after correcting those
lands, thicker copper would reduce only its associated resistance; it would
not remove connector drop, regulator tolerance or transient effects. Keep
the current explicit stack until the alternative has been checked end to end.

The completed staff clarification is distinct from the remaining engineering
review. No fabrication release is implied by these requirement decisions.
