# Selected package and pinout review — October 27

We compared the following BOM variants and saved pads with manufacturer
package drawings and pin tables. This closes these specific checks; it is
not a claim that every footprint, solder process or mechanical installation
has been qualified. No component or footprint changed in this pass.

| References / exact variant | Saved footprint and manufacturer comparison | Pinout result |
| --- | --- | --- |
| U40–U42, TPS564252DRLR | Six-pin SOT-563/DRL, 0.50 mm pitch. Saved pads are 0.675 × 0.35 mm, with row centers 1.425 mm apart. TI's DRL0006A example uses 0.67 × 0.30 mm and 1.48 mm row spacing. The library pattern differs slightly from that example but covers the stated terminal locations; it is not a wrong-package selection. | 1 VIN, 2 SW, 3 GND, 4 PG, 5 EN, 6 FB match all three regulator nets. |
| U1, INA180A2IDBVR | Five-pin DBV/SOT-23, 0.95 mm pitch. Saved pads are 1.325 × 0.60 mm, with row centers 2.275 mm apart. TI's example uses 1.10 × 0.60 mm at 2.60 mm row spacing. The existing pads extend farther inward and still overlap the terminal region. | **A pinout**: 1 OUT, 2 GND, 3 IN+, 4 IN−, 5 VS. The B variant swaps functions and is not a drop-in substitution. A2 gives the intended 50 V/V gain. |
| U81, SN74LVC14APWR | PW is TSSOP-14, nominal 5.0 × 4.4 mm body, 0.65 mm pitch. Saved pads are 1.475 × 0.40 mm at 5.725 mm row spacing; TI's example uses 1.50 × 0.45 mm at 5.80 mm. The pitch, pin count and lead span match the selected package. | Supply 14, ground 7; encoder input/output pairs 1/2, 3/4, 5/6 and 9/8 match. Unused inputs 11/13 are grounded and outputs 10/12 are unconnected. |
| D40, **Diotec** BZT52C12 | Diotec explicitly specifies **SOD-123F**, matching D_SOD-123F. Other manufacturers sell similarly named parts in SOD-123, so the manufacturer must remain part of the purchase identity. | Pad 1 cathode reaches the protected MOSFET-source rail; pad 2 anode reaches the gate, matching the intended gate clamp. |

The package examples are reference land patterns, not the only allowed pad
sizes. Small differences do not justify replacing working footprints without
checking lead overlap, spacing and assembly method. Conversely, a matching
part name alone is insufficient: package suffixes and pinout variants matter.
The current native DRC passes, including the existing local SOT-563 pad
clearance rule. We did not relax rules or alter paste apertures for this check.

We also reran the existing placement checks for the five GCT switch contact
pairs/pads and the bottom Pi socket's forty physical pin coordinates, drill
sizes and 58 × 49 mm mounting pattern. Those checks pass. L298/heatsink
installation and the rest of the manufacturer drawing audit remain separate
from the package checks above. Actual socket mating and solder quality are
assembly checks.

References: [TPS564252 pin table and DRL0006A drawing](https://www.ti.com/lit/ds/symlink/tps564252.pdf),
[INA180 pinout A/B and DBV0005A drawing](https://www.ti.com/lit/ds/symlink/ina180.pdf),
[SN74LVC14A pin table and PW0014A drawing](https://www.ti.com/lit/ds/symlink/sn74lvc14a.pdf),
[Diotec BZT52C12 package identity](https://diotec.com/en/product/BZT52C12.html).

## Seventeen additional components

We checked the saved pad coordinates and critical pin nets against the
following selected variants. All 17 pass the reproducible checks in
`check_selected_packages.py`; [Selected-package-check.json](Selected-package-check.json)
records each result and the unchanged PCB hash. Small land-pattern differences
below are deliberate library differences, not package substitutions.

| References / variant | Package and land-pattern comparison | Pinout result |
| --- | --- | --- |
| U11/U15/U21/U25/U31/U35, SN65HVD231DR | SOIC-8, 1.27 mm pitch. Saved pads 1.95 × 0.60 mm, row centers 4.95 mm; TI example 1.55 × 0.60 mm at 5.40 mm. Saved pads extend inward but overlap the specified lead region. | D/ground/VCC/R/NC/CANL/CANH/RS agree with pins 1–8. RS is grounded; pin 5 is unused. |
| U2/U3, ACS712ELCTR-05B-T | SOIC-8, 1.27 mm pitch. Same saved pads; Allegro example 1.75 × 0.65 mm at 5.60 mm. Body and lead span match; this does not qualify the high-current copper thermally. | 1/2 IP+, 3/4 IP−, 5 ground, 6 filter, 7 output, 8 supply match. |
| Q1, DMPH3010LK3-13 | TO-252. Saved lead spacing 4.56 mm versus nominal 4.572 mm; lead pads 2.2 × 1.2 mm and tab pad 6.4 × 5.8 mm overlap the package terminals. | 1 gate, 2 drain/tab, 3 source. The tab carries fused battery voltage; it is not ground. |
| U10/U14/U20/U24/U30/U34, MCP2515T-I/ST | ST suffix is TSSOP-20, 4.4 × 6.5 mm body, 0.65 mm pitch. Saved pads 1.475 × 0.40 mm at 5.725 mm rows; manufacturer example 1.45 × 0.45 mm at 5.90 mm. Lead regions overlap. | All 20 pin assignments checked, including TSSOP-specific SPI, reset, clock, supply and unused pins. Do not use the SOIC pin numbering. |
| U50/U60, STM32F401RET6TR | LQFP-64, 10 × 10 mm body, 12 mm nominal lead span and 0.50 mm pitch. Saved pads 1.55 × 0.30 mm at 11.35 mm opposite-row centers cover the specified leads. | VBAT, all supply/ground pins, VDDA, VCAP, reset, boot and SWD agree. GPIO mapping remains covered by the separate pin-map/connection checks. |

Sources: [TI SN65HVD231](https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf),
[Allegro ACS712](https://www.allegromicro.com/-/media/files/datasheets/acs712-datasheet.pdf),
[Diodes DMPH3010LK3](https://www.diodes.com/datasheet/download/DMPH3010LK3.pdf),
[Microchip MCP2515, TSSOP drawing and land pattern](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2515-Family-Data-Sheet-DS20001801K.pdf),
[ST STM32F401 pin table and LQFP64 drawing](https://www.st.com/resource/en/datasheet/stm32f401re.pdf).

The remaining manufacturer audit covers inductors, connectors/fuse hardware,
remaining discrete parts and the L298 installation. Solder-process suitability,
current capacity and mechanical fit are separate from pad/pinout agreement.
