# Regulator circuit and placement review

25 October 2026. We checked the three TPS564252 circuits, refined their
placement and added initial local routing. This completes the pin/divider
review and local connectivity pass; it does not qualify the supplies or finish
board-wide power distribution. See [Routing-review.md](Routing-review.md).

## Circuit checks

The exported netlist matches VIN/SW/GND/PG/EN/FB pin numbering. Each switching
node connects only to its regulator and inductor. Input/output bypass,
feedback, feed-forward, enable dividers, 3.3 V power-good pull-ups and test
headers pass the independent checks in `check_netlist.py`.

We kept the existing parts and voltage setpoints. `check_power_stage.py` reads
the actual BOM resistors and saved PCB to produce [Power-stage-check.json](Power-stage-check.json).

| Rail | Nominal | Static reference/resistor corners | EN voltage upper bound at 15 V input |
| --- | ---: | ---: | ---: |
| Servo | 6.600 V | 6.384–6.822 V | 2.675 V |
| Pi/devices | 5.100 V | 5.015–5.186 V | 3.542 V |
| Logic | 3.318 V | 3.215–3.424 V | 4.752 V |

Output corners use the reference's full-temperature limits and resistor
tolerances (0.1% for Pi, 1% otherwise). They exclude wiring drop, ripple and
transients. EN uses 1% external resistor corners and ignores the internal
pulldown, which gives a conservative upper pin-voltage bound. All three are
below 5.5 V. Their typical turn-on thresholds are not battery cutoffs.

At 15 V input, 600 kHz and −20% inductance, the allocated-load inductor peaks
are 4.819/4.046/1.373 A; RMS currents are 4.028/3.328/0.866 A. These are below
the listed 6.7 A saturation and 5.8 A DC temperature-rise test points, but omit
frequency variation, core loss, hot derating and inductance rolloff with current.
The regulator can reach a 6.7 A **valley** limit before ripple is added, so this
comparison does not establish inductor suitability during a fault.

## Placement change

Previously, SW faced left while the inductor sat to the right of the IC. We
rotated U40–U42 by 180°, brought L1–L3 closer, placed output capacitors beside
the output end of each inductor, and grouped feedback components on the quiet
side of each IC. Thirty footprint positions/orientations changed. Pad numbers,
electrical nets and unrelated component placement stayed unchanged.

The SW-to-inductor pad-center distance fell from 7.388 mm to 2.964 mm. The new
100 nF-to-VIN distance is 2.015 mm and FB-to-top-resistor distance is 2.515 mm.
These distances describe placement, not trace lengths or a tested noise limit.

Initial routing now includes local power connections, ground vias and a
separate output-sense trace. We still need to review the Kelvin feedback ground
return, switching-loop geometry, effective capacitor values under DC bias and the control
loop. Thermal performance remains unverified; the manufacturer's 2 oz
evaluation board does not establish a rating for our 1 oz board. No additional
team measurements were needed for this review.

## References and verification

- [TI TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf), pinout, electrical limits and design/layout guidance.
- [Eaton SDCHA1V80 datasheet](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf), 4R7 rating conditions. Its layout guidance also advises against traces/vias underneath the inductor.
- [Fabrication-check.json](Fabrication-check.json) records the current ERC/DRC/parity results and remaining routing blockers. The board is not released for fabrication.
