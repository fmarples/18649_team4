# Digital design review

## Current revision — October 29

The [latest staff guidance](Course-updates-October29.md) closes the extra-L298-
protection requirement question and the prescribed-hole question. Additional
hardware protection and the FPV camera are optional. The current PCB and
power budget do not include either addition; engineering qualification remains
separate from those requirement decisions.

The selected LiPo pair, PA3 sensing circuit and standalone cutoff logic are
documented in [Battery-LiPo.md](Battery-LiPo.md). The current board contains
300 electrical footprints and 20,264 track/via items. All 331 targeted
connections and fresh native ERC/DRC/parity checks pass. The selected-package
check covers 186 components, including the added six crystals, encoder LDO,
two VDDA beads and 136 selected passive parts. This is a package/pinout check,
not full operating qualification. We previously corrected C802's package and
widened 779 power-track segments; see [Power-route-revision.md](Power-route-revision.md).

We replaced the regulator bank capacitors with 25 V 1210 parts and added
parallel capacitors: 66 uF at each input and 88/66/66 uF at the servo/Pi/logic
outputs. The feed-forward capacitors are now 68/91/30 pF. We rerouted the new
connections and moved twelve ground vias away from the enlarged solder pads.
The [capacitor review](Capacitor-bank-review.md) records the calculations and
their limits: typical bias curves and assumed aging/temperature allowances
are not guaranteed combined minimum capacitance or a complete loop assessment.

We use the subsequently selected CAD rear pair A1/A2: 47.870 mm front spacing,
73.01493 mm rear spacing and 233.21155 mm between rows. The team confirmed
the new rear holes are unused and accessible and supplied supporting measurements.
The earlier cardboard test checked the previous pattern. We use 4 mm round
NPTH holes for M3 screws and washers. The chassis
holes have 4 mm exclusions measured from the finished hole edge; the Pi holes
keep their 3 mm edge exclusions. The check covers components and copper on
all four layers. See [Mounting-tolerance-revision.md](Mounting-tolerance-revision.md).
This does not turn the earlier cardboard test into a test of the revised pattern.

Full Pi supply margin, capacitor/control-loop and thermal qualification,
motor/fuse protection, application cutoff integration and final manufacturing
review remain open. Final mating and retention checks occur during assembly.
No fabrication release or powered-board test is claimed.

## Earlier revision — October 27

The [mounting and encoder revision](Mounting-and-encoder-revision.md) supersedes
older socket, heatsink-placement and encoder-voltage statements below. All
eight supports now meet the 3 mm hole-edge rule; HS80 is installed; encoders
have a separate 4.0 V supply. Current JSON checks carry the active board hash.
The subsequent 5 V cell relocation improves the calculated Pi feed from
4.8662 to 4.9116 V at the 3 A allocation, before local return/contact/hot/dynamic
losses. All 308 targeted checks and fresh native ERC/DRC/parity pass. There
are 287 electrical footprints and 19,513 track/via items. The package script
now checks 28 components, adding the four Hirose headers, three inductors
and four LED transistors. A published typical capacitor-model comparison
is recorded without changing the selected parts. See
[Power-stage-review.md](Power-stage-review.md),
[Power-margin-review.md](Power-margin-review.md) and
[Critical-package-review.md](Critical-package-review.md).

**Release work recorded October 27:** battery/charger and motor-fault decisions; complete
Pi feed/return/contact/thermal/dynamic budget; exact input/output capacitor
and loop qualification; remaining fuse/discrete/assembly-process review;
servo mating-part rating and stock reconciliation; final exports and review.
Heatsink placement, encoder supply correction and hole-edge clearance are
complete in CAD. Historical open items below are superseded where those
corrections apply. No physical operation or fabrication release is claimed.

## Earlier review record


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
| Current sensing and regulator geometry | Confirmed separate shunt sense traces with no shared load-trace objects. Measured local input/SW/FB and feedback-return paths. The bulk ground DC model is now complete for its stated cases; local connections and switching noise remain outside it. |
| Labels and apertures | Added readable interface/button labels, pin signals and a numbered legend. Inspected native front silk and mask/paste plots. C7 keeps thermal relief at a 45-degree spoke angle. |
| Circuit/package consistency | Netlist/pad checks pass. Manufacturer package/pinout checks now cover U40–U42, U1, U81, D40, both MCUs, all six CAN controllers/transceivers, both ACS712 sensors and Q1; see [Critical-package-review.md](Critical-package-review.md). The Pi socket and switch geometry checks remain valid. Inductors, connectors/fuse hardware, remaining discretes and L298 installation still need the relevant drawing/process checks. |
| Power-margin sensitivity | Compared CAN, encoder and Pi limits separately; calculated capacitor-retention targets, feed-forward zeros/poles, converter ripple/loss and L298 cooling requirements. Four independent numerical tests pass; results were regenerated for the wider supply copper. Setpoints and BOM did not change in this pass. See Power-margin-review.md. |
| Bulk ground-plane DC loss | Extracted saved In1 fill, modeled three DC current cases on three meshes with two port radii, and compared load grounds with feedback-reference grounds. Four independent sheet-solver tests pass. Positive Pi ground offsets are 2.6–6.5 mV in these cases; local connections, contacts and dynamics are excluded. See [Ground-plane-review.md](Ground-plane-review.md). |
| Heatsink mounting research | Defined the 6396BG anchors, M3 tab clamp, hardware and nominal height from Boyd/ST drawings. A nearby U80/sink placement reduces the fin/web screen to C800, C802 and J80. The candidate is not yet applied. See [Heatsink-mounting-review.md](Heatsink-mounting-review.md). |
| Nominal mechanical fit | Recomputed Pi heights, engagement and support/socket distances from saved CAD; defined plug/cooler selection envelopes and microSD service access. A conditional main-board/tire screen gives 8.75 mm, or 3.75 mm with a 5 mm sensitivity allowance. Complete vehicle sweep and actual mating remain assembly checks. See [Mechanical-evidence.md](Mechanical-evidence.md). |

The component centers, pad shapes/nets, mounting geometry, CAN backbone and
project rules are unchanged by the preceding width-only pass. R430/R431 retain the
precision parts selected in the previous revision. The schematic PDF,
current CSV BOMs, board previews and verification reports describe this revision.
The ground-plane and additional package reviews change no CAD/BOM files.
The subsequent mechanical review adds a library-only heatsink footprint and
specifies its mounting kit in two purchasing-BOM rows; it does not alter the
active schematic or PCB. Fresh placement/netlist checks pass. Prior native
ERC/DRC results still match the unchanged active CAD hashes.

## Findings that still prevent release

- **Supply design:** add local return connections, contacts and regulator
  load/line behavior to the Pi/logic budget; the bulk-plane screen is complete
  for its stated scenarios. Improve the Pi feed further if required. The encoder
  connector is below its recorded 3.3 V range endpoint even before return
  losses. Establish the encoder's permitted range or select a suitable supply.
  The Pi screen cannot guarantee freedom from low-voltage warnings. These
  findings are design calculations, not observed failures.
- **Converters:** obtain exact input/output capacitor bias/aging/ESR data or
  select documented alternatives, then settle the feed-forward values. The
  completed sensitivity review does not establish full-loop stability. Finish
  the cooling assessment after the input/load envelope and heatsink placement
  are fixed. The drawing-based tab/anchor arrangement is now specified.
- **Design choices:** settle the battery/charger and input protection, L298
  fault expectations, Pi mounting-margin
  interpretation and servo mating-part rating. These affect the design;
  no repeat chassis measurements are requested.
- **Heatsink implementation:** install the specified two-anchor footprint,
  move U80 and the affected neighbors, reroute and check the copper. Mounting
  research is complete; this CAD work does not depend on new measurements.
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
- [Ground-plane model and contact sensitivity](Ground-plane-review.md),
  [mesh results](Ground-plane-check.json) and
  [selected package checks](Selected-package-check.json).

Run the `check_*.py` tools with KiCad's bundled Python. Run
`check_power_stage.py` before `check_load_allocation.py` and
`check_supply_paths.py`, since they use its component-tolerance results.
The native audit uses a fresh output directory and records source hashes.
The native checks and downstream reports were regenerated after the copper
change. Run `check_power_margins.py` with ordinary Python
after the upstream reports; `python -m unittest test_power_margins.py` checks
its arithmetic independently. The four numerical tests do not replace DRC
or qualify the operating assumptions.
The ground model uses KiCad Python for extraction and a separate interpreter
with NumPy/SciPy/Shapely for solving; see Ground-plane-review.md for commands.
Its four additional numerical tests validate the solver independently.
