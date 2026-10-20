# Lab 4: three-zone controller PCB

We are designing a two-layer KiCad PCB with two STM32F401RET6 chips, six
MCP2515/CAN-transceiver interfaces, motor and servo current sensing, and an
AA-powered supply. The Raspberry Pi remains a separate board connected through
its 40-pin header.

**Status, 20 October 2026:** partial schematic and calculated design for review.
The schematic contains 149 components across the overview and four zone/power
sheets. It is not ready for fabrication. No PCB layout or hardware validation
is included.

## Shared report and files

- [Lab 4 Writeup](https://docs.google.com/document/d/1zMR_S5QoFPES1BhswG5bhpLGAib2P71ri6rK2hKzBcc/edit): edit this same report for future revisions.
- [Team Lab 4 Drive folder](https://drive.google.com/drive/u/1/folders/1j7L880-h1lnl-udWRu19jh2Ww-18leLq).
- [Editable system diagram](Lab4-System.drawio), with [SVG](Lab4-System.svg) and [PNG](Lab4-System.png) previews.

The shared Google Doc is the report. This repository holds the editable design
sources, technical calculations and verification records.

## Design files

| File | Contents |
| --- | --- |
| [KiCad/Lab4.kicad_pro](KiCad/Lab4.kicad_pro) | Open this project in KiCad 10. |
| [KiCad/Lab4.kicad_sch](KiCad/Lab4.kicad_sch) | Overview linking the Front, Rear, Cockpit and Power sheets. |
| [Lab4-Circuits.pdf](Lab4-Circuits.pdf) | Five-page schematic preview. |
| [Pin-map.csv](Pin-map.csv) | Per-zone signal names, physical pins, modes and unresolved integration notes. |
| [Power-design.html](Power-design.html) | Proposed power tree, component calculations and validation limits. |
| [Power-budget.csv](Power-budget.csv) | Four rail allocations; average loads remain unmeasured. |
| [Power-calculations.json](Power-calculations.json) | Calculated regulator ripple, peak current and enable thresholds. |
| [Preliminary-BOM.csv](Preliminary-BOM.csv) | Placed quantities and additional planned parts, with procurement status. |
| [KiCad/Circuit-BOM.csv](KiCad/Circuit-BOM.csv) | The 149 components currently placed in the schematic. |
| [Design-review.csv](Design-review.csv) | Remaining engineering decisions and checks. |
| [Interface-review.csv](Interface-review.csv) | Interface allocation notes. |
| [Measurements-to-record.csv](Measurements-to-record.csv) | Blank mechanical and electrical measurement record. |
| [Verification.txt](Verification.txt) | Checks performed and their limits. |
| [KiCad/ERC.txt](KiCad/ERC.txt) | Unresolved electrical-rule findings. |
| [circuit-pin-connections.json](circuit-pin-connections.json) | Placed component pin/net metadata for comparison with the schematic. |

Keep the local `Lab4_Power.kicad_sym`, `Lab4_Power.pretty`, `sym-lib-table` and
`fp-lib-table` beside the KiCad project. Their paths use `${KIPRJMOD}` and travel
with the repository. The other footprints come from the standard KiCad library.

## Power and pin decisions

We selected AA cells in series and propose ten rechargeable NiMH cells for
nominal 12 V. Exact cells, holder, capacity, charger and runtime remain undecided.
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

The proposed Pi mapping is A=CE0/IRQ25 and B=CE1/IRQ24. Confirm the installed
device-tree configuration and physical bus labels before relying on Linux
`can0`/`can1` enumeration.

## Remaining work

- Complete bare-MCU support, Pi connector, L298/flyback/current limiting,
  actuator and encoder wiring, LEDs, buttons and test-point integration.
- Join the hierarchical sheets deliberately. Same-name local labels on
  different sheets are not connected in this partial design.
- Select the actual AA cells/holder, fuse element, high-current input landing,
  final protection and mechanically compatible heatsink. J40's generic signal
  header footprint remains a placeholder, not the battery connector choice.
- Verify exact transceiver ordering code, crystal loading, capacitor bias,
  custom footprint dimensions, supply transients and thermal behavior.
- Measure the chassis, set the board outline/mounting holes, preserve service
  access, route the board and complete DRC, fit checks and fabrication outputs.

ERC currently reports **24 findings: 18 errors and 6 warnings**. Most reflect
missing host/power drivers and incomplete connections. Three shared SPI MISO
output conflicts need an accurate tri-state MCP2515 symbol review; do not
disable the general output-conflict check. No ERC/DRC pass is claimed.

## Rechecking with KiCad

From this directory, with `kicad-cli` from KiCad 10 on PATH:

```sh
kicad-cli sch export pdf -o Lab4-Circuits.pdf KiCad/Lab4.kicad_sch
kicad-cli sch erc -o KiCad/ERC.txt KiCad/Lab4.kicad_sch
```

PDF export checks that KiCad can parse the project. ERC checks electrical
connectivity; neither proves component ratings, footprint dimensions, thermal
performance or fabrication readiness. Record any changed findings rather than
assuming that successfully exporting the PDF means the board is complete.
