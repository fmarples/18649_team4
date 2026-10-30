# Lab 4: three-zone controller PCB

The PCB is named **649 Team 4**. The October 30
[identification update](Silkscreen-identification-review.md) adds all three
members' names to the silkscreen and records the explicit four-layer fabrication
stack. Routing, component placement and electrical calculations are unchanged.

We are designing a four-layer KiCad PCB with two STM32F401RET6 chips, six
MCP2515/CAN-transceiver interfaces, motor and servo current sensing, and a
3S LiPo supply using the CNHL S220403BK / Hitec 44295 pair approved by Anson on October 28. The Raspberry Pi remains a separate board connected through
its 40-pin header.

The [October 29 course updates](Course-updates-October29.md) close the question
of whether extra L298 hardware protection is mandatory (it is optional) and
confirm that rigid mounting, rather than a prescribed hole set, is required.
The optional camera is not included in the current power allocation. The saved
copper stack is unchanged; 2 oz would require a revised manufacturing review.

We selected the required scope only: keep the course L298 and omit extra
hardware current limiting and the camera. The [input-fuse review](Fuse-and-scope-review.md)
and [Pi conductor mesh](Pi-feed-review.md) are complete for their stated
assumptions. The 3 A mesh is retained as a deferred stress case; the current
load-specific result and limitations are in [Prototype-operating-review.md](Prototype-operating-review.md). No optional-circuit decision or new hole measurement
is holding up the review. The [Lab 1 revision history](https://docs.google.com/document/d/182TcM6g2DfyiQt0xGXAkl2lv_5BjBLEOPw9v7Lpieis)
now records the October 29 hardware configuration.

## October 28 capacitor and chassis allowance revision

The latest [power-route/package correction](Power-route-revision.md) widens
779 power segments and fixes C802 to the manufacturer's D10/P5 footprint.
All native checks and 331 targeted connections pass; the October 29
[package audit](Critical-package-review.md) now covers 282 components.
The L298 uses a local footprint with 1.1 mm finished plated holes for better
lead-clearance tolerance; pin centers, copper pads and heatsink anchors are unchanged.
These checks cover the listed package geometry and critical pin nets, not
complete operating qualification. The [review export](review-package/REVIEW-ONLY.txt)
contains matching schematic/layer PDFs, 3D views, Gerbers/drills and BOM/CPL
files. It is ready for the course
prototype fabrication review, with no order or TA acceptance claimed.
[Prototype-operating-review.md](Prototype-operating-review.md) separates the
completed planning review from required assembly/bring-up checks and optional stress work.

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
an order. The current planning review is complete; team/TA review precedes
fabrication, and harness/fuse selection, cutoff integration and controlled
powered validation precede LiPo use. The capacitor
selection and routing revision is implemented; loop/transient and thermal
behavior still require qualified review and later prototype validation.



The reference [layer stack](Layer-stack.md) and initial
[return-path review](Return-path-review.md) document the copper assumptions and remaining checks.
The [supply-path screening](Supply-path-review.md) includes shared-load allocation;
remaining voltage and thermal findings are listed in the power-margin review.
The [CAN geometry audit](CAN-geometry-review.md) records branch lengths and
the repaired sampled ground reference. The [solder-via review](Solder-via-review.md)
records the completed overlap correction and remaining mask/assembly checks.
On October 26 staff explicitly allowed four-layer boards. The saved PCB now
uses F.Cu / In1.Cu ground / In2.Cu signals / B.Cu, with inner-layer keep-outs. Teams
should plan stencil assembly, not assume board-house assembly. See the dated
course updates in Fabrication-review.md.
The last checked two-layer layout is preserved at the
[lab4-two-layer-archive tag](https://github.com/fmarples/18649_team4/tree/lab4-two-layer-archive/lab4)
(commit `59be0b1`). It is a historical, partially routed checkpoint; use the
current `lab4` branch for further design work.

The selected [LiPo battery and charger](Battery-LiPo.md) replace the historical
NiMH candidates. Anson approved the exact Amazon pair; all other new parts
must use DigiKey/Mouser or confirmed course stock. The existing Drive purchasing
workbook matches the current active CSV. A selection/approval is not
an order or a completed hardware test.

The October 24 team reply relays Anson's acceptance of the 6396BG heatsink
and deferral of motor stall/L298 loss/temperature measurements for that
preliminary review. Its drawing-based mounting arrangement is now implemented;
thermal performance and motor-fault protection are still unvalidated. The
TAs confirmed on October 23 that teams will assemble all SMD parts themselves,
with TechSpark oven access tentative. BOM-Hand-assembly.csv is the active
assembly list; use course v3 stock first. This is not a fabrication or
purchasing release. The October 24 review covered schematic, BOM and high-level
design; the board layout deadline is October 29.

## Shared report and files

- [October 29 fabrication review](Fabrication-review.md): remaining design decisions,
  final deliverables and fresh-check instructions. The October 24 preliminary
  package was emailed; the final Gradescope/fabrication submission remains open.
- [October 29 must-do list](https://docs.google.com/document/d/1k5grd6PXWf11GlPkxlc1w4cDT9LOGJRj_YvyB7UWkLg/edit): team actions and decision targets.
- [Lab 4 Writeup](https://docs.google.com/document/d/1zMR_S5QoFPES1BhswG5bhpLGAib2P71ri6rK2hKzBcc/edit): edit this same report for future revisions.
- [Team Lab 4 Drive folder](https://drive.google.com/drive/u/1/folders/1j7L880-h1lnl-udWRu19jh2Ww-18leLq).
- [Editable system diagram](Lab4-System.drawio), with [SVG](Lab4-System.svg) and [PNG](Lab4-System.png) previews.

The shared Google Doc is the report. This repository holds the editable design
sources, technical calculations and verification records.

Lab 4 disables Git line-ending conversion locally through `.gitattributes`.
The engineering reports and review manifest hash exact file bytes; preserving
them makes the checked CAD/export files consistent across checkouts and Git
archives. A text-only line-ending change still requires refreshing its hashes.

Use this `lab4/` directory on the `lab4` branch as the source of truth for
KiCad files, local libraries, the editable diagram, BOMs and engineering tables.
Drive holds the shared report, original course references and raw measurement
evidence. There is no automatic synchronization between GitHub and Drive;
link to these design files from Drive instead of uploading editable copies.

When the design changes, regenerate the affected schematic PDF, BOM and checks
from the same source revision and commit them together. Record the commit used
for a TA submission so the reviewed version can be recovered later.

## Design files

| File | Contents |
| --- | --- |
| [KiCad/Lab4.kicad_pro](KiCad/Lab4.kicad_pro) | Open this project in KiCad 10. |
| [KiCad/Lab4.kicad_sch](KiCad/Lab4.kicad_sch) | Overview linking the Front, Rear, Cockpit and Power sheets. |
| [KiCad/Lab4.kicad_pcb](KiCad/Lab4.kicad_pcb) | Editable 120 × 247.21155 mm PCB with all required connections routed; electrical release review remains open. |
| [Placement-overview.png](Placement-overview.png) | Direct Pi stack: bottom socket and top circuitry above the Pi. |
| [Pi-stack-side-view.png](Pi-stack-side-view.png) | Proposed 22 mm Pi gap and 35 mm chassis spacers; physical fit pending. |
| [Placement-detail.svg](Placement-detail.svg) | Native KiCad component outlines and references. |
| [Placement-fit-template.pdf](Placement-fit-template.pdf) | Two-page true-size PCB/Pi fit aid, side view and measurement fields; not a drill template. |
| [Placement-review.md](Placement-review.md) | Placement decisions, verification results and remaining work. |
| [Placement-check.json](Placement-check.json) | Netlist, outline, Pi-space and mounting-margin checks. |
| [KiCad/Placement-DRC.json](KiCad/Placement-DRC.json) | Fresh native DRC and schematic parity: zero findings and zero missing connections. |
| [Lab4-Circuits.pdf](Lab4-Circuits.pdf) | Five-page schematic preview. |
| [Pin-map.csv](Pin-map.csv) | Per-zone signal names, physical pins, modes and unresolved integration notes. |
| [Power-design.html](Power-design.html) | Proposed power tree, component calculations and validation limits. |
| [Power-budget.csv](Power-budget.csv) | Four rail allocations; average loads remain unmeasured. |
| [Current-evidence.md](Current-evidence.md) | Why existing Lab 2 logs cannot establish calibrated average current. |
| [Current-measurements.csv](Current-measurements.csv) | Rail/condition record for the remaining measurements. |
| [Parts-review.md](Parts-review.md) | Course v3 reconciliation, documented selections and physical checks. |
| [Course-stock-v3.csv](Course-stock-v3.csv) | Exact named course-stock parts and source links. |
| [Review-package.md](Review-package.md) | October 24 deliverables and remaining review decisions. |
| [Power-calculations.json](Power-calculations.json) | Calculated regulator ripple, peak current and enable thresholds. |
| [Preliminary-BOM.csv](Preliminary-BOM.csv) | Placed quantities and additional planned parts, with procurement status. |
| [KiCad/Circuit-BOM.csv](KiCad/Circuit-BOM.csv) | The 300 components currently placed in the schematic. |
| [BOM-Hand-assembly.csv](BOM-Hand-assembly.csv) | Active course/team-assembly procurement view. |
| [BOM-JLC-hybrid.csv](BOM-JLC-hybrid.csv) | Historical catalog comparison; not the selected course assembly plan. |
| [Assembly-options.md](Assembly-options.md) | Process differences, equipment and sourcing checks. |
| [Actuator-design.md](Actuator-design.md) | Motor, encoder, servo and lamp circuits; ratings and connector pin definitions. |
| [Design-review.csv](Design-review.csv) | Earlier preliminary-review snapshot; its battery, mounting and routing status is superseded by the current shared must-do list and dated reviews above. |
| [Interface-review.csv](Interface-review.csv) | Interface allocation notes and actual host-pin/net connections. |
| [Measurements-to-record.csv](Measurements-to-record.csv) | Confirmed mounting geometry and remaining physical/electrical measurements. |
| [Verification.txt](Verification.txt) | Checks performed and their limits. |
| [KiCad/ERC.txt](KiCad/ERC.txt) | Current schematic: zero errors/warnings; engineering limitations remain. |
| [check_netlist.py](check_netlist.py) | Repeatable connectivity/BOM checks on a KiCad XML export. |
| [circuit-pin-connections.json](circuit-pin-connections.json) | Placed component pin/net metadata for comparison with the schematic. |

Keep the local `Lab4_Power.kicad_sym`, `Lab4_Logic.kicad_sym`, `Lab4_Power.pretty`,
`Lab4_Mechanical.pretty`, `Lab4_Mechanical.3dshapes`, `sym-lib-table` and
`fp-lib-table` beside the KiCad project. Their paths use `${KIPRJMOD}` and travel
with the repository. The other footprints come from the standard KiCad library.

## Power and pin decisions

We selected the TA-approved CNHL S220403BK 3S LiPo and Hitec 44295 charger.
Amazon is permitted for both. All active new non-battery/charger purchases
use DigiKey/Mouser or explicitly requested course stock. The pack body fits
the measured battery envelope with the supplier's dimensional allowance;
actual retention and wiring are assembly checks. Old NiMH entries have zero
purchase quantity. See [Battery-LiPo.md](Battery-LiPo.md) for ratings, wiring,
charging and the implemented divider/standalone cutoff guard. MCU integration,
power-filter qualification and motor/fuse protection are not complete.
The proposed branches are the unregulated motor supply, 6.6 V servo buck,
5.1 V Pi/devices buck and 3.318 V logic buck. The protected-input electrical
target is 8–15 V; this does not define the cells' allowed discharge voltage.

The pin proposal uses the Lab 3 candidate/WCET overlays at commit `c4fba58` as
its baseline. Lab 3 CAN, timing and LED assignments are retained or reserved.
PB11 is unavailable in the STM32F401RE's LQFP64 package, so PC9 is proposed for
that PID marker; PC8 remains the WCET task probe. New actuator and ADC signals
avoid those timing pins. This branch does not implement or flash the PCB
firmware changes. Pin-map.csv is a signal allocation, not a complete MCU
power/decoupling pinout.

Both bare-MCU support circuits are now placed: VDD bypass capacitors, filtered
VDDA, reset and BOOT0 circuits, separate reset/self-test buttons, SWD and UART
headers. Each MCU's VCAP1 pin has its own **4.7 µF** capacitor to ground, as
specified for LQFP64 in the [STM32F401RE datasheet](https://www.st.com/resource/en/datasheet/stm32f401re.pdf).
VCAP1 is an internal-regulator output, not a GPIO or a 3.3 V supply input.
The initial clock plan uses internal HSI/PLL; the Nucleo ST-LINK clock is absent.

We added the Pi socket, twelve diagnostic LEDs with individual 1 kΩ
resistors, and probe rows matching the Lab 3 handout. Extra probes have separate
headers. The Pi's 3.3 V output remains disconnected from the PCB's independent
3.3 V regulator. Do not connect separate USB-C power while the board supplies
the Pi through pin 4; power-path isolation is not implemented.

J70 is a bottom-mounted Samtec ESQ-118-44-L-D socket covering Pi pins 3–38, aligned
directly to a component-side-up Pi below the main PCB. No GPIO cable is planned.
Top-side cockpit CAN circuitry occupies part of that same area. We propose
22 mm Pi spacers and 35 mm chassis spacers, now supported by the October 24
Pi caliper measurements and nominal clearance calculations in
[Mechanical-evidence.md](Mechanical-evidence.md). Actual assembly is untested. See the
placement review for contact insertion, underside-tail limits, cooling/Wi-Fi
checks. The implemented 3 mm Pi hole-edge exclusions pass the saved-board audit.

The root sheet explicitly joins the power, ground and two CAN backbones.
SPI, clocks, reset and actuator signals remain within their owning zones.
The local MCP2515 symbol marks SO as tri-state, matching
[Microchip DS20001801K, Figure 12-11](https://www.microchip.com/content/dam/mchp/documents/APID/ProductDocuments/DataSheets/MCP2515-Family-Data-Sheet-DS20001801K.pdf).
The general ERC output-conflict check stays enabled. The local Pi symbol treats
the board-fed 5 V/GND connector pins as inputs and its hidden stacked pins as
passive; this avoids an implicit global 5 V connection. Power flags identify
the battery, regulator outputs and supplies after passive filters; they do not
prove voltage regulation or available current.

The proposed Pi mapping is A=CE0/IRQ25 and B=CE1/IRQ24. Confirm the installed
device-tree configuration and physical bus labels before relying on Linux
`can0`/`can1` enumeration.

## Remaining work by stage

- Before fabrication: team/TA review of the matched prototype package and its
  stated operating assumptions, then the team's Gradescope submission by
  **Saturday October 31, 10 p.m.** The [extension](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793301588360959)
  includes staff review before the fabrication batch. No new hole measurements
  or sustained 3 A Pi qualification are requested.
- Before ordering/assembly: reconcile actual stock, settle the servo lead and
  solder process. Current purchasing exceptions remain visible in the BOM.
- Before LiPo operation: staged bench commissioning, fuse/harness selection,
  battery-guard application integration and physical/electrical acceptance.
  These remain required; see [the operating review](Prototype-operating-review.md).
- Optional/deferred: sustained 3 A Pi tests, extra peripherals/current limiter,
  deliberate stall tests, a 2 oz redesign and expanded simulation.

## Rechecking with KiCad

From this directory, with `kicad-cli` from KiCad 10 on PATH:

```sh
kicad-cli sch export pdf -o Lab4-Circuits.pdf KiCad/Lab4.kicad_sch
kicad-cli sch erc -o KiCad/ERC.txt KiCad/Lab4.kicad_sch
kicad-cli sch export netlist --format kicadxml -o lab4-check.xml KiCad/Lab4.kicad_sch
python check_netlist.py lab4-check.xml
```

PDF export checks that KiCad can parse the project. ERC checks electrical
connectivity; neither proves component ratings, footprint dimensions, thermal
performance or fabrication readiness. Record any changed findings rather than
assuming that successfully exporting the PDF means the board is complete.
The XML is a temporary check artifact; it need not be committed.
