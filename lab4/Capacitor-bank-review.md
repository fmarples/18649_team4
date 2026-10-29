# Revised power capacitor banks

28 October 2026. We replaced the six 0805 buck-output capacitors with
1210 parts and added ten capacitors. All nineteen bank capacitors are
Murata GRM32ER61E226KE15L: 22 µF, 25 V, X5R, ±10%.
The separate C700 Pi bypass remains the original 0805 part.

| Converter | Input bank, plus existing 100 nF | Output bank | Feed-forward capacitor |
| --- | --- | --- | --- |
| Servo U40 | C410/C415/C416: 66 µF nominal | C412/C413/C417/C418: 88 µF nominal | C414: 68 pF |
| Pi/5 V U41 | C420/C425/C426: 66 µF nominal | C422/C423/C427: 66 µF nominal | C424: 91 pF |
| Logic U42 | C430/C435/C436: 66 µF nominal | C432/C433/C437: 66 µF nominal | C434: 30 pF |

The old 22 µF input and two small 22 µF output parts lost too much capacitance
under bias in our design screen. The replacement uses the existing 25 V input
part in larger parallel banks. Its [manufacturer characteristic sheet, p.3](https://static.chipdip.ru/lib/973/DOC031973461.pdf)
provides typical bias/ESR curves. The [DigiKey listing](https://www.digikey.com/en/products/detail/murata-electronics/GRM32ER61E226KE15L/965931)
identifies the exact purchased part. We request nineteen plus four spares.

## Capacitance calculation

We round the typical plot toward more loss: 65% at 12.6 V input, 70% at the
15 V circuit-review ceiling, and 40/25/20% at the servo/Pi/logic upper
setpoint screens (6.82/5.19/3.38 V). We then multiply by 0.90 tolerance,
0.85 temperature and an additional **assumed** 0.80 aging factor.
These factors form a conservative planning sensitivity; they are not a
manufacturer-guaranteed combined minimum or measured values.

| Bank | Screened effective capacitance | Comparison |
| --- | ---: | --- |
| Each input, 12.6 V | 14.14 µF | Above TI's >10 µF recommendation |
| Each input, 15 V | 12.12 µF | Above the same recommendation |
| Servo output | 32.31 µF | LC pole 17.26 kHz with assumed 2.63 µH |
| Pi output | 30.29 µF | LC pole 17.83 kHz with assumed 2.63 µH |
| Logic output | 32.31 µF | LC pole 17.26 kHz with assumed 2.63 µH |

`check_capacitor_banks.py` reproduces the arithmetic and checks actual BOM
MPNs/footprints. At 2.63 µH, a 20 kHz LC pole requires 24.08 µF.
[TI's design guidance](https://www.ti.com/lit/ds/symlink/tps564252.pdf),
§8.2.2.2–8.2.2.4, calls for effective capacitance and places the pole around
20 kHz. This is a design guideline, not a sharp stability threshold.
Our 66/88 µF nominal outputs fall within the relevant 22–88/44–88 µF
reference ranges. The 2.63 µH case is the earlier inductor-rolloff sensitivity,
not a guaranteed minimum at every load and temperature.

## Feed-forward choice and ripple

We changed C414/C424/C434 to 68/91/30 pF, C0G, 50 V, ±5%, in the same 0603
footprints. Exact MPNs are GRM1885C1H680JA01D, GRM1885C1H910JA01D and
GRM1885C1H300JA01D. All have DigiKey sources in the purchasing BOM.

The servo and Pi values put the passive-divider zero near 23.4 and 23.3 kHz,
using `1/(2π Rtop Cff)`. This closely follows the 24.1 kHz zero in TI's
5 V example while accounting for our different feedback resistances.
The 30 pF logic value follows TI's 3.3 V example with our almost identical
45.3 kΩ/10 kΩ divider. All three are within TI's 10–100 pF guidance.
This is a documented reference-design choice, not a claimed full-loop
phase-margin measurement or simulation. TI's available transient model is
encrypted for PSpice; we have not run it in KiCad/ngspice.

The existing CCM sensitivity reaches 2.107 A RMS input ripple and 1.021 A RMS
output ripple on the servo converter. Three input capacitors would each
carry 0.702 A if they shared equally; actual routing and ESR prevent assuming
exact sharing. For scale, assigning **all** 2.107 A to one capacitor at an
assumed 30 mΩ ESR gives 0.133 W; equal sharing gives 0.0148 W per input
capacitor. These are `I²R` examples, not a temperature prediction or ripple
rating. The manufacturer plot is roughly a few milliohms near switching
frequency under its typical test conditions; it does not guarantee hot,
biased ESR. Keep the capacitors below their 85 °C operating limit.

The original close 100 nF/input capacitor paths and main power routing are
preserved. Added parts have dedicated copper branches and ground vias;
some bulk branches use the back layer. Their inductance means the sum of
low-frequency capacitances is not a guarantee of high-frequency decoupling.
After assembly, test startup, output ripple and representative load changes
with short probe grounding, then inspect capacitor, regulator and inductor
temperatures. These are prototype validation steps, not claimed measurements.

We relocated twelve existing ground vias exposed by the larger output pads,
keeping finished drill edges outside the solder lands with the existing
0.15 mm nominal drill-separation sensitivity. Ground branches remain connected.
Ordinary same-net electrical DRC does not detect solder wicking; the separate
Solder-via-check.json records that geometry check. Final mask/paste inspection
and the assembly process still need review.
