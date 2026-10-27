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
