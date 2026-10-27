# Digital design review — October 27



The four-layer PCB is fully connected, with 284 electrical footprints,

16,605 trace segments and 973 vias. Fresh ERC, DRC and schematic comparison

have zero findings; all 306 targeted connection checks pass. We have not

released the board for fabrication or tested a built PCB.



## Completed in this revision



| Review | Result |

| --- | --- |

| Supply currents and static voltage | The latest pass widens 768 logic and 541 five-volt segments. Worst logic feed drop falls from 144 to 95 mV; Pi feed drop falls from 159 to 150 mV. The 0.1% logic divider is retained. Ground/contact/heating/transient losses remain outside this screen. |

| Drill and aperture clearance | Moved 32 existing vias. No nominal drill/land overlaps or sites inside the 0.15 mm screen remain. This is not a mask-registration or tenting guarantee. |

| CAN topology | Measured main paths, bus-side branches and local transceiver connections; reviewed their scale against edge time and TI's stub guidance. No added length-matching meanders. Sampled references remain present. |

| Current sensing and regulator geometry | Confirmed separate shunt sense traces with no shared load-trace objects. Measured local input/SW/FB and feedback-return paths. Shared ground copper still needs a loss/noise assessment. |

| Labels and apertures | Added readable interface/button labels, pin signals and a numbered legend. Inspected native front silk and mask/paste plots. C7 keeps thermal relief at a 45-degree spoke angle. |

| Circuit/package consistency | Netlist/pad checks pass. Manufacturer package and pinout review is complete for U40–U42, U1, U81 and D40; see [Critical-package-review.md](Critical-package-review.md). The Pi socket and switch geometry checks remain valid. The remaining package review is not claimed complete. |

| Power-margin sensitivity | Compared CAN, encoder and Pi limits separately; calculated capacitor-retention targets, feed-forward zeros/poles, converter ripple/loss and L298 cooling requirements. Four independent numerical tests pass; results were regenerated for the wider supply copper. Setpoints and BOM did not change in this pass. See Power-margin-review.md. |



The component centers, pad shapes/nets, mounting geometry, CAN backbone and

project rules are unchanged by this width-only pass. R430/R431 retain the

precision parts selected in the previous revision. The schematic PDF,

current CSV BOMs, board previews and verification reports describe this revision.



## Findings that still prevent release



- **Supply design:** complete the Pi/logic return and total-loss budget after

  the present feed widening; improve the Pi feed further if required. The encoder

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

  [placement](Placement-check.json) and [supply-width comparison](Supply-copper-change.json).

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

The native checks and downstream reports were regenerated after the copper

change. Run `check_power_margins.py` with ordinary Python

after the upstream reports; `python -m unittest test_power_margins.py` checks

its arithmetic independently. The four numerical tests do not replace DRC

or qualify the operating assumptions.

