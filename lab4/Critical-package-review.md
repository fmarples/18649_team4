# Selected package and pinout review — October 27

## October 28 bulk-capacitor and clamp review

The reproducible audit now covers **41 components**. We corrected C802:
Panasonic EEU-FR1E471 is **10 mm diameter × 12.5 mm body length, 5 mm lead
pitch**, with 0.6 mm leads. The previous D8/P3.5 footprint was incorrect.
The saved D10/P5 footprint has 2 mm pads and 1 mm plated holes, with pad 1
on protected battery and pad 2 on ground. The BOM and schematic now agree.
[Panasonic series drawing](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf),
[exact part record](https://na.industrial.panasonic.com/products/capacitors/aluminum-electrolytic-capacitors/series/83367/model/83716).

We checked C400 (Nichicon UPW1E102MHD) against its 12.5 mm diameter,
20 mm body length and 5 mm pitch; its existing footprint matches. C804/C805
use AVX TPS B-case tantalums, 3.5 × 2.8 mm body and 2.1 mm maximum height.
Their band denotes the **positive anode**, which is pad 1; pad 2 is ground.
Do not apply the aluminum-can negative-stripe convention to these tantalums.
[AVX TPS drawing and electrical limits](https://datasheets.kyocera-avx.com/TPS.pdf).

All eight SMC SK520B clamps use the SMB package and correct cathode/anode
nets. Saved pads are 2.5 × 2.3 mm at ±2.15 mm centers, covering the
manufacturer terminal regions. For every motor output, the lower diode
points from ground to output and the upper diode from output to protected
battery. Pad 1 is the banded cathode. This matters because the diodes carry
motor recirculation current when the bridge switches.
[SMC N0952 revision A](https://www.smc-diodes.com/propdf/SK520B%20N0952%20REV.A.pdf).

These checks establish the listed package identities, geometry and polarity.
Ripple, temperature and motor-fault duty are separate from package fit.
Earlier counts below describe earlier review stages.

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
pairs/pads and the bottom Pi socket's retained physical pin coordinates (Pi3–38), drill
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

## Eleven further package checks

The saved-pad check now covers 28 components. Four MMBT3904-7-F lamp
transistors have base/emitter/collector on pads 1/2/3. Their 1.475 × 0.60 mm
lands at 1.875 mm row spacing cover the specified SOT23 lead region; they
differ from Diodes' 0.90 × 0.80 mm suggested pattern at 2.00 mm rows.
The diode and transistor footprints must not be interchanged based on
their three-pad appearance. [Diodes DS30036, pp.1 and 6](https://www.diodes.com/datasheet/download/MMBT3904.pdf).

L1–L3 match Eaton's 8.5 mm outer land span, 2.8 mm inner gap and 6.6 mm
land width. The 0.15 mm-or-thicker paste recommendation needs reconciliation
with the eventual assembly process; a correct footprint does not resolve
that process choice. [Eaton ELX1097, p.3](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf).

J40/J80/J81/J90 match the Hirose straight-header drawing: 3.96 mm pitch,
1.8 mm terminal holes and a 1.6 mm guide hole offset 1.5 × 3.25 mm.
Their battery/motor/servo pin assignments also match the schematic.
This closes the board-header geometry check, not the mating harness or
crimp qualification. The catalog's straight-header hand-solder condition
is 290 °C for 3 seconds; the solid ground pads need suitable preheating
and technique rather than unlimited dwell. [Hirose drawing and catalog](https://www.hirose.com/en/product/p/CL0680-0567-0-00).

Keystone explicitly lists holder 3568 for Littelfuse 297 MINI fuses and
rates the holder at 30 A. This closes the fuse-family compatibility lookup;
it does not select the fuse current or prove coordination with the battery,
wiring and PCB. The October 28 drill-pattern comparison is recorded below.
[Keystone 3568](https://www.keyelco.com/product.cfm/product_id/306).

Remaining drawing/process work covers the other discrete/passive packages
and the chosen soldering process.
The integrated L298/heatsink installation is reviewed separately in
Mounting-and-encoder-revision.md. Current capacity, capacitor behavior and
thermal qualification remain separate from the passed pad/pinout checks.

## Fuse-holder drill pattern — October 28

We checked the exact Keystone 3568 revision C drawing: four holes on a
9.92 × 3.40 mm pattern, minimum hole diameter 1.60 mm. The saved F1 footprint
has this pattern and 1.78 mm plated drills. The extra 0.18 mm nominal drill
diameter is consistent with the drawing's minimum-hole requirement; it is
not evidence of assembled retention or fuse coordination. Both duplicated
pad-1 terminals reach BAT_PLUS and both pad-2 terminals reach BAT_FUSED.
The reproducible package check now covers 29 components. No footprint change
was needed. [Manufacturer drawing](https://www.keyelco.com/product-pdf.cfm?p=306),
[readable copy of drawing 3568 C](https://www.allelcoelec.pt/datasheets.c4/3568.pdf).
