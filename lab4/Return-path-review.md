# Ground, feedback and supply routing review

26 October 2026. This is a review of the saved copper, not a powered test or
fabrication release. [Return-path-check.json](Return-path-check.json) records
the board hash and geometric/connectivity observations. Run
`check_return_paths.py` with KiCad Python to regenerate it; use the native DRC
report for disconnected copper islands.

## Connections and remaining geometry checks

The three lower feedback resistors have explicit copper paths to their
regulators' ground pins, even when zone objects are excluded from the graph.
Their pad-center separation is 6.729 mm. This establishes connectivity, not a
quiet Kelvin return: a path can still share copper with switching current.
Before release, review the actual feedback branch and input/output capacitor
return geometry against the [TPS564252 layout guidance](https://www.ti.com/lit/ds/symlink/tps564252.pdf),
especially the separate feedback return, compact input loop and wide output
capacitor return. Effective capacitance under DC bias remains a separate check.

Both INA180 inputs have explicit paths to the corresponding R1 shunt pads.
Keep these as separate sense branches at the shunt terminals when completing
the servo load route; do not move a sense connection onto a distant power
trace. The [INA180 layout guidance](https://www.ti.com/lit/ds/symlink/ina180.pdf)
calls for Kelvin connections and closely matched input routing. Final loop
area and noise coupling still need review. U2/U3 are ACS712 magnetic current
sensors; their motor-current paths need a width/return review, not external
shunt-input routing.

## CAN ground transitions

We added twenty ground vias near CAN signal-layer transitions. The placement
search targeted sites with no ground via or ground through-hole pad within
3 mm, then added a clear site within 2.5 mm. These distances are design-review
targets, not a manufacturer signal-integrity limit. The JSON records every
CAN signal via's distance to the nearest ground transition.

The plane-centerline samples also include ordinary pad/via clearance holes.
A sampled void is a location to inspect, not automatically an electrical
failure. Check the filled In1 plane and bottom ground fill, especially where
routes change layers. [Layer-stack.md](Layer-stack.md) explains why In2 signals
also need the nearby B.Cu reference reviewed. Pair spacing, branch lengths
and controlled impedance are not yet qualified.

## Supply resistance check still required

The new 3.3 V joins connect the main MCU/CAN supply groups to the regulator;
two encoder pull-ups remain disconnected. The new local 5 V branches are not
the complete regulator-to-load network. Main Pi, servo and motor feeds are
unfinished.

As a calculation example, using copper resistivity 1.72e-8 ohm-metres at about
20 degrees C, a 100 mm long, 0.8 mm wide trace has resistance
`R = resistivity * length / (width * thickness)`:

| Copper thickness | Calculated resistance | Drop at assumed 0.8 A |
| --- | ---: | ---: |
| 0.0152 mm inner copper | 0.141 ohm | 0.113 V |
| 0.035 mm outer copper | 0.0614 ohm | 0.0491 V |

These examples exclude vias, connectors, return resistance and heating, and
are not a calculation of the complete board. Use actual branch loads and
route lengths to check the worst load voltage, then widen or parallel supply
trunks as needed. Check thermal current capability separately. A successful
connectivity check alone does not settle either requirement.
