# Lab 4: three-zone controller PCB

We are designing a four-layer KiCad PCB with two STM32F401RET6 chips, six
MCP2515/CAN-transceiver interfaces, motor and servo current sensing, and a
NiMH-powered supply with a battery/charger purchase still to finalize. The Raspberry Pi remains a separate board connected through
its 40-pin header.

**Status, 27 October 2026:** all required PCB connections are routed, with
zero missing connections and zero native DRC/ERC/schematic-parity findings.
All 306 targeted connection checks pass. Current allocation, CAN branches,
nominal drill/aperture clearance, labels and current mask/paste plots have
been reviewed. We widened 474 logic-supply segments, selected precision
feedback resistors and cleared 32 remaining near-aperture via sites. The
[power-margin review](Power-margin-review.md) adds verified calculations for
voltage limits, capacitance, feed-forward behavior and heat. Encoder supply
qualification, Pi/logic feed/return refinement, exact capacitor data and final
cooling/battery/protection/mechanical decisions remain open. The board is not
released for fabrication. See [Digital-review.md](Digital-review.md).
See [Routing-review.md](Routing-review.md) for the completed scope and limits.
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
The five schematic pages contain 284 components and 298 nets. The proposed
120 x 234 mm PCB contains 284 assigned electrical footprints and eight
mechanical supports. The four chassis centers use the team's caliper measurements:
50 mm front, 105 mm rear, 220 mm longitudinal separation and aligned pair
midpoints. Chassis holes are confirmed smooth, 4.5 mm through-holes;
M3/3.2 mm PCB drills remain a proposal.

Tenergy 11609 with charger 01025 was the earlier design/BOM baseline.
The October 24 [TA reply](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792870041277289)
requires DigiKey or Mouser for parts outside the course list. Its
[17:44 EDT follow-up](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792878299024869)
allows Amazon for the battery only, preferably Prime one- or two-day delivery
to Pittsburgh. Charger sourcing remains unresolved. See Parts-review.md for
documented candidates; no replacement has been finalized.
The October 24 team reply relays Anson's acceptance of the proposed 6396BG
heatsink and confirms that motor stall/L298 loss/temperature measurements
are not needed for today's review. Mounting hardware is a staff follow-up;
thermal performance and protection behavior are not validated. Battery mounting
and procurement decisions remain unresolved. The TAs confirmed on October 23 that
teams will assemble all SMD parts themselves, with TechSpark oven access tentative.
BOM-Hand-assembly.csv is the active assembly list; use course v3 stock first. Power/CAN review, power/heatsink decisions,
physical fit and hardware validation are unfinished. This is not a fabrication
or purchasing release. The October 24 review covers schematic, BOM and high-level
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
| [KiCad/Lab4.kicad_pcb](KiCad/Lab4.kicad_pcb) | Editable 120 x 234 mm PCB with all required connections routed; electrical/thermal and mechanical review remains open. |
| [Placement-overview.png](Placement-overview.png) | Direct Pi stack: bottom socket and top circuitry above the Pi. |
| [Pi-stack-side-view.png](Pi-stack-side-view.png) | Proposed 22 mm Pi gap and 35 mm chassis spacers; physical fit pending. |
| [Placement-detail.svg](Placement-detail.svg) | Native KiCad plot with pads and references. |
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
| [KiCad/Circuit-BOM.csv](KiCad/Circuit-BOM.csv) | The 284 components currently placed in the schematic. |
| [BOM-Hand-assembly.csv](BOM-Hand-assembly.csv) | Active course/team-assembly procurement view. |
| [BOM-JLC-hybrid.csv](BOM-JLC-hybrid.csv) | Historical catalog comparison; not the selected course assembly plan. |
| [Assembly-options.md](Assembly-options.md) | Process differences, equipment and sourcing checks. |
| [Actuator-design.md](Actuator-design.md) | Motor, encoder, servo and lamp circuits; ratings and connector pin definitions. |
| [Design-review.csv](Design-review.csv) | Remaining engineering decisions and checks. |
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

Battery and charger purchasing remain unresolved. Amazon is now permitted
for the battery only; the charger still needs a permitted source or a specific
exception. Tenergy 11609/01025 and the unqualified Dantona alternatives are
zero-quantity reference rows. One pack and one compatible charger are
explicit unresolved requests; see Parts-review.md. The team checked
a 115x50x50mm cardboard battery envelope between the chassis plates and
reported approximately 51.75mm usable height. Strap/lead routing, wiring,
cost and lead time remain; see Parts-review.md.
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

We added the Pi 40-pin socket, twelve diagnostic LEDs with individual 1 kΩ
resistors, and probe rows matching the Lab 3 handout. Extra probes have separate
headers. The Pi's 3.3 V output remains disconnected from the PCB's independent
3.3 V regulator. Do not connect separate USB-C power while the board supplies
the Pi through pins 2/4; power-path isolation is not implemented.

J70 is now a bottom-mounted Samtec ESQ-120-44-L-D socket candidate, aligned
directly to a component-side-up Pi below the main PCB. No GPIO cable is planned.
Top-side cockpit CAN circuitry occupies part of that same area. We propose
22 mm Pi spacers and 35 mm chassis spacers, now supported by the October 24
Pi caliper measurements and nominal clearance calculations in
[Mechanical-evidence.md](Mechanical-evidence.md). Actual assembly is untested. See the
placement review for contact insertion, underside-tail limits, cooling/Wi-Fi
checks and the Pi mounting-hole clearance interpretation that remains open.

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

## Remaining work

- Resolve the 3.2 A motor stall specification against the L298N's 2 A DC/braking
  limits. The schematic has no autonomous motor current limiter; the filtered
  ADC and pack fuse do not establish one. Select the heatsink for the agreed load.
- Finalize battery retention/lead routing and purchasing, the selected fuse candidate's qualification, operating stop voltage, wiring
  and exact connector/contact compatibility. J40/J80/J81 now use Hirose power
  connectors. October 24 servo and pictured motor/encoder wire mappings are
  documented in Actuator-design.md; second-harness agreement, physical mating
  and completed-adapter continuity remain unverified.
- The encoder supply correction is implemented: J82/J83 use nominal 3.3V.
  Validate its tolerance and the actual encoder signals before operation. See Parts-review.md for this finding and
  the selected spacer, fastener, shunt, LED and harness part numbers.
- Finalize component quantities from course stock and the additional-parts request.
  The course assembly plan is now team assembly; the JLC comparison is historical.
- The five GCT switch footprints and contact pairs are verified and placed;
  see [Switch-footprint-review.md](Switch-footprint-review.md). Review remaining
  package/connector dimensions and the course-stock transceiver's DR code.
- The four chassis positions, Pi paper footprint and actual-Pi height checks
  are complete; no repeat measurements are requested. Before layout freeze,
  resolve remaining cable/port/steering envelopes using drawings or a quick
  unpowered check where necessary. Check actual mating and retention at assembly.
  Complete routing, power/thermal design and final DRC before fabrication.

ERC reports zero errors and zero warnings. Netlist checks cover all 284
references and 297 nets, including motor current paths, flyback polarity,
servo supply after its shunt, MCU support and Lab 3 pin reservations.
DRC reports zero ordinary violations and zero missing footprints. Its
unconnected list and full saved-board connectivity count both report 31.
Partial routing contains 15,594 segments, 879 vias and six ground zones.
A package-specific 0.15 mm pad-clearance rule applies only inside U40-U42
for the proposed 1 oz copper process; general trace clearance stays 0.20 mm.
See Placement-review.md for the source and remaining limits.

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
