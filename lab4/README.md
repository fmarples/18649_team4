# Lab 4: three-zone controller PCB

We are designing a two-layer KiCad PCB with two STM32F401RET6 chips, six
MCP2515/CAN-transceiver interfaces, motor and servo current sensing, and an
AA-powered supply. The Raspberry Pi remains a separate board connected through
its 40-pin header.

**Status, 20 October 2026:** partial schematic and calculated design for review.
The schematic contains 236 components across the overview and four zone/power
sheets. It is not ready for fabrication. No PCB layout or hardware validation
is included.

## Shared report and files

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
| [Lab4-Circuits.pdf](Lab4-Circuits.pdf) | Five-page schematic preview. |
| [Pin-map.csv](Pin-map.csv) | Per-zone signal names, physical pins, modes and unresolved integration notes. |
| [Power-design.html](Power-design.html) | Proposed power tree, component calculations and validation limits. |
| [Power-budget.csv](Power-budget.csv) | Four rail allocations; average loads remain unmeasured. |
| [Power-calculations.json](Power-calculations.json) | Calculated regulator ripple, peak current and enable thresholds. |
| [Preliminary-BOM.csv](Preliminary-BOM.csv) | Placed quantities and additional planned parts, with procurement status. |
| [KiCad/Circuit-BOM.csv](KiCad/Circuit-BOM.csv) | The 236 components currently placed in the schematic. |
| [Design-review.csv](Design-review.csv) | Remaining engineering decisions and checks. |
| [Interface-review.csv](Interface-review.csv) | Interface allocation notes and actual host-pin/net connections. |
| [Measurements-to-record.csv](Measurements-to-record.csv) | Blank mechanical and electrical measurement record. |
| [Verification.txt](Verification.txt) | Checks performed and their limits. |
| [KiCad/ERC.txt](KiCad/ERC.txt) | Current partial schematic: zero errors/warnings. |
| [check_netlist.py](check_netlist.py) | Repeatable connectivity/BOM checks on a KiCad XML export. |
| [circuit-pin-connections.json](circuit-pin-connections.json) | Placed component pin/net metadata for comparison with the schematic. |

Keep the local `Lab4_Power.kicad_sym`, `Lab4_Logic.kicad_sym`, `Lab4_Power.pretty`, `sym-lib-table` and
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

- Complete L298/flyback/current limiting, final motor/encoder and servo
  connectors, encoder voltage conditioning and vehicle-lamp drivers.
- Verify the GCT switch drawing and assign the five missing switch footprints;
  select exact header/socket parts and check their mechanical orientation.
- Select the actual AA cells/holder, fuse element, high-current input landing,
  final protection and mechanically compatible heatsink. J40's generic signal
  header footprint remains a placeholder, not the battery connector choice.
- Verify exact transceiver ordering code, crystal loading, capacitor bias,
  custom footprint dimensions, supply transients and thermal behavior.
- Measure the chassis, set the board outline/mounting holes, preserve service
  access, route the board and complete DRC, fit checks and fabrication outputs.

ERC currently reports **zero errors and zero warnings** for the placed circuits.
The exported netlist passes support-circuit, host-pin, probe-order and cross-zone
connectivity checks. Five switch footprints remain unassigned and several
actuator/protection circuits are absent: a clean ERC does not establish board
completeness. No layout DRC or hardware validation is claimed.

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
