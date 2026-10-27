# Digital design review — October 27

The four-layer PCB is fully connected, with 284 electrical footprints,
16,605 trace segments and 973 vias. Fresh ERC, DRC and schematic comparison
have zero findings; all 306 targeted connection checks pass. We have not
released the board for fabrication or tested a built PCB.

## Completed in this revision

| Review | Result |
| --- | --- |
| Supply currents and static voltage | Assigned loads to shared trunks, widened 474 logic segments and specified 0.1% logic-divider resistors. Lowest calculated logic load voltage is 3.119 V in the stated case, before return/heating/transient losses. |
| Drill and aperture clearance | Moved 32 existing vias. No nominal drill/land overlaps or sites inside the 0.15 mm screen remain. This is not a mask-registration or tenting guarantee. |
| CAN topology | Measured main paths, bus-side branches and local transceiver connections; reviewed their scale against edge time and TI's stub guidance. No added length-matching meanders. Sampled references remain present. |
| Current sensing and regulator geometry | Confirmed separate shunt sense traces with no shared load-trace objects. Measured local input/SW/FB and feedback-return paths. Shared ground copper still needs a loss/noise assessment. |
| Labels and apertures | Added readable interface/button labels, pin signals and a numbered legend. Inspected native front silk and mask/paste plots. C7 keeps thermal relief at a 45-degree spoke angle. |
| Circuit/package consistency | Fresh netlist verifies regulator pin mapping, polarity, switch contact pairs, interfaces and BOM identities. Placement check verifies the Pi socket pin coordinates and mounting pattern. Assignment/parity does not replace every manufacturer's package drawing. |
| Power-margin sensitivity | Compared CAN, encoder and Pi limits separately; calculated capacitor-retention targets, feed-forward zeros/poles, converter ripple/loss and L298 cooling requirements. Four independent numerical tests pass. No CAD or BOM change in this analysis pass. See Power-margin-review.md. |

The component centers, pad shapes/nets, mounting geometry, CAN backbone and
project rules are unchanged. R430/R431 retain their nominal values and 0603
footprints; only their resistor tolerance/MPNs change. The schematic PDF,
current CSV BOMs, board previews and verification reports describe this revision.

## Findings that still prevent release

- **Supply design:** refine the Pi/logic feed and return model and improve
  geometry as required. The calculated CAN margin is small; the encoder
  connector is below its recorded 3.3 V range endpoint even before return
  losses. Establish the encoder's permitted range or select a suitable supply.
  The Pi screen cannot guarantee freedom from low-voltage warnings. These
  findings are design calculations, not observed failures.
- **Converters:** obtain exact input/output capacitor bias/aging/ESR data or
  select documented alternatives, then settle the feed-forward values. The
  completed sensitivity review does not establish full-loop stability. Finish
  the cooling assessment after the input/load envelope and heatsink placement
  are fixed; a detailed thermal model with guessed attachment is premature.
- **Design choices:** settle the battery/charger and input protection, L298
  fault expectations, heatsink attachment/envelope, Pi mounting-margin
  interpretation and servo mating-part rating. These affect the design;
  no repeat chassis measurements are requested.
- **Purchasing and exports:** reconcile course stock and the two precision
  resistor changes with the previously uploaded purchasing snapshot. Generate
  and inspect final manufacturing files after affected design changes.

Loaded voltage, ripple, ADC noise, converter temperature, CAN waveforms and
adapter continuity are assembly/bring-up checks. They cannot be reported as
measurements of an unbuilt board. The remaining CAD/component-data work does
not require a new general measurement campaign.

## Reproducible evidence

- [Fabrication audit](Fabrication-check.json), [routing](Routing-check.json),
  [placement](Placement-check.json) and [revision comparison](Routing-change-check.json).
- [Supply allocation and limitations](Supply-path-review.md),
  [per-load results](Load-allocation-check.json),
  [regulator calculations](Power-stage-review.md), and
  [voltage/capacitor/thermal sensitivities](Power-margin-review.md) with
  [reproducible results](Power-margin-check.json).
- [CAN review](CAN-geometry-review.md), [return/sense review](Return-path-review.md),
  [measured path geometry](Digital-geometry-check.json),
  [drill/aperture review](Solder-via-review.md).
- [Resistor procurement change](Parts-review.md#logic-divider-tolerance-change--october-27).

Run the `check_*.py` tools with KiCad's bundled Python. Run
`check_power_stage.py` before `check_load_allocation.py` and
`check_supply_paths.py`, since they use its component-tolerance results.
The native audit uses a fresh output directory and records source hashes.
The later calculation-only pass leaves CAD/BOM hashes unchanged, so those
native results still apply. Run `check_power_margins.py` with ordinary Python
after the upstream reports; `python -m unittest test_power_margins.py` checks
its arithmetic independently. The four numerical tests do not replace DRC
or qualify the operating assumptions.
