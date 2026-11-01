# November 1 staff-review correction

We corrected the submitted `6945466` design for the staff's latest guidance.
The original Gradescope submission and staff file receipt remain valid records
of that earlier revision. This correction needs a replacement handoff and staff
review; we have not sent it or placed a fabrication order.

## Circuit correction

[Bill's November 1 instruction](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793564724174489)
places the flyback clamps between the current sensor and motor connector.
We changed D800.2/D801.1 from `LEFT_BRIDGE` to `LEFT_MOTOR`, and D804.2/D805.1
from `RIGHT_BRIDGE` to `RIGHT_MOTOR`, in both the schematic and PCB. The
return-terminal diodes already clamped the motor-connector nets. Diode
polarity, the battery/ground ends, and the ACS712 current-path pins are unchanged.

The sensors now measure current in the series bridge branch. Some PWM
recirculation current flows through the motor-side diodes without crossing
the sensor. We corrected the report's broader winding-current wording; later
calibration and firmware must respect this distinction.

## Copper and design rules

We adopted the relevant checks from
[Tom's example](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793566288076649):

- Minimum copper connection width: **0.1524 mm (6 mil)**.
- Clearance from either CAN bus to a copper zone: **0.381 mm (15 mil)**.
- Copper-to-board-edge clearance: **0.508 mm (20 mil)**.
- Existing 0.2 mm general clearance/track-width, 0.2 mm annular-ring and
  0.3 mm via-drill rules remain. The documented 0.15 mm internal SOT563-pad
  exception remains stricter than Tom's example.

We refilled the planes and repaired the resulting narrow junctions with
local copper bridges, wider short segments and a 0.25 mm minimum zone width.
Non-ground additions on In1 only join nearby same-net plated contacts; the
routing check requires both ends at those contacts and a length below 2 mm.
They are not new long signal routes across the ground plane.

J504.1, J605.1 and J70.34 retain thermal relief, with adjusted spoke angles
and explicit 0.3 mm ground spokes. Y14's grounded case pad 4 uses its explicit
ground track instead of a narrow extra zone connection. No additional pad
was changed to a solid plane connection in this revision.

All **309 footprints**, pad dimensions/drills, orientations and positions are
unchanged. Only the four named diode pad nets changed. The board now contains
**20,296 track/via items** and six ground zones. The
[revision comparison](November1-review-check.json) records those checks.
No part, procurement quantity, mounting hole, board outline or stack changed.

## Verification and limits

Fresh native ERC, DRC, schematic parity and unconnected counts are **zero**,
including a fresh zone refill. All **331 targeted connection checks** pass;
the package check covers **282 components**. The updated netlist check also
rejects the old diode topology, demonstrating that the correction is tested.
Mounting, heatsink, digital/CAN geometry, return-path, solder-via and capacitor
checks were rerun. Exported drill coordinates and all 300 position rows are
compared with the saved board separately.

The wider CAN clearance creates 41 reference-plane sample gaps outside the
older 1 mm hole-exclusion screen. All 41 fall inside the deliberately cleared
area around CAN plated contacts; none is an unexplained new remote plane gap.
The geometry report retains and classifies them. This does not establish
continuous reference copper through those contacts or measured signal integrity.

We reran the supply paths, ground-plane model and both Pi meshes after changing
copper. The 0.05 mm mesh gives **35.578 mV** positive-feed loss at the 1.5 A Pi
planning load (67.995 mV at the deferred 3 A stress load). The stated
hot-copper/contact/return assumptions still give **4.916–4.934 V** before
transients. Planning pack current remains **2.19–2.50 A**. These are calculations,
not powered tests; see [Prototype-operating-review.md](Prototype-operating-review.md).

Earlier dated revision reports retain their historical comparisons. Current
native results and exact source hashes are in
[Fabrication-check.json](Fabrication-check.json); current manufacturing files
and hashes are in [review-package](review-package/manifest.json).

The remaining steps are staff review/handoff, stock and assembly choices, then
controlled bring-up. Startup, temperature, installed fuse/harness qualification
and application-level battery-cutoff testing are still required before LiPo
driving. The deferred sustained 3 A case has not become a new fabrication task.
