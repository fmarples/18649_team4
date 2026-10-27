# Regulator circuit and placement review

27 October 2026. We checked the three TPS564252 circuits, their routed local
connections and feedback dividers. The supplies are connected, but their
effective capacitance, control-loop behavior and thermal performance are not
yet qualified. See [Routing-review.md](Routing-review.md).

## Circuit checks

The exported netlist matches VIN/SW/GND/PG/EN/FB pin numbering. Each switching
node connects only to its regulator and inductor. Input/output bypass,
feedback, feed-forward, enable dividers, 3.3 V power-good pull-ups and test
headers pass the independent checks in `check_netlist.py`.

We kept the voltage setpoints and changed R430/R431 to 0.1% resistors. `check_power_stage.py` reads
the actual BOM resistors and saved PCB to produce [Power-stage-check.json](Power-stage-check.json).

| Rail | Nominal | Static reference/resistor corners | EN voltage upper bound at 15 V input |
| --- | ---: | ---: | ---: |
| Servo | 6.600 V | 6.384–6.822 V | 2.675 V |
| Pi/devices | 5.100 V | 5.015–5.186 V | 3.542 V |
| Logic | 3.318 V | 3.263–3.373 V | 4.752 V |

Output corners use the reference's full-temperature limits and resistor
tolerances (0.1% for Pi and logic, 1% for servo). They exclude wiring drop, ripple and
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

Routing now includes local power connections, ground vias, a separate
output-sense trace and explicit feedback-resistor ground branches for all three
regulators. The routed-path review below records their geometry. Shared-return
noise, effective capacitance under DC bias and control-loop behavior remain
unqualified. Thermal performance remains unverified; the manufacturer's 2 oz
evaluation board does not establish a rating for our 1 oz board. No additional
team measurements were needed for this review.

## Output-filter sensitivity

Each buck has two GRM219R61C226ME15L capacitors, or 44 uF nominal.
We used the effective capacitance in TI's equation
`f = 1 / (2*pi*sqrt(L*C))` to see how loss of capacitance changes the LC
pole. With the selected 4.7 uH inductor at its -20% tolerance:

| Assumed total effective capacitance | Calculated LC pole |
| --- | ---: |
| 44 uF | 12.37 kHz |
| 33 uF | 14.29 kHz |
| 22 uF | 17.50 kHz |
| 16.84 uF | 20.00 kHz |
| 11 uF | 24.75 kHz |

These are sensitivity cases, not measured or manufacturer-specified values
for these capacitors. About 16.84 uF gives TI's approximate 20 kHz design
target at the low-inductance corner. This is not a guaranteed stability
boundary. The remaining component check is the actual combined capacitance
after voltage bias, tolerance, temperature and aging at each rail voltage,
followed by the complete loop/transient review. We cannot count the full
44 uF as effective capacitance merely because it is the BOM value. The
calculation is recorded in `Power-stage-check.json`.

## References and verification

- [TI TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf), pinout, electrical limits and design/layout guidance.
- [Eaton SDCHA1V80 datasheet](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf), 4R7 rating conditions. Its layout guidance also advises against traces/vias underneath the inductor.
- [Fabrication-check.json](Fabrication-check.json) records the current ERC/DRC/parity results and remaining engineering limits. The board is not released for fabrication.

## Routed geometry, capacitor and thermal findings — October 27

[Digital-geometry-check.json](Digital-geometry-check.json) measures the same
local pattern for each regulator: VIN to 100 nF is 1.974 mm, SW to inductor
2.415 mm and FB to its resistor 2.720 mm, all without vias. The explicit
lower-divider return is 9.250 mm on front copper. The output-sense paths are
44.811 mm for servo/logic and 25.148 mm for the relocated 5 V cell. These
are on the quiet output nets, not the high-impedance FB nodes.
These whole-item lengths identify geometry for review, not loop inductance.
The return shares ground copper, so it is not an isolated Kelvin ground.

For the selected 22 µF ±20% X5R capacitors, nominal 44 µF becomes 29.92 µF
with −20% tolerance and −15% temperature before DC bias and aging. Reaching
16.84 µF then requires at least 56.3% of that remaining capacitance. This is
a calculated requirement, not the part's verified DC-bias retention. The
exact manufacturer bias/model data could not be obtained in this review;
that specific component-data check remains open. See
[Murata's DC-bias explanation](https://www.murata.com/en-eu/support/faqs/capacitor/ceramiccapacitor/char/0005).

The TI table recommends 3.3 µH at 3.3 V and 4.7 µH at 5 V; it does not have
a 6.6/7 V row. Our common 4.7 µH choice therefore needs its calculated LC
and feed-forward review, rather than a claim that every rail copies a table.
The 22 pF feed-forward parts remain starting values, not validated tuning.

Using typical 25 °C switch resistances and 12 V input, conduction-only loss
is about 0.665 W for the 4 A servo allocation, 0.412 W for 3.3 A on 5 V and
0.024 W for 0.8 A on 3.3 V. These omit switching and hot-resistance effects.
TI's 74 °C/W effective figure is for its 2 oz EVM; its 137.4 °C/W JEDEC figure
is a comparison metric. Neither establishes our board's temperature. Thus
4 A continuous servo operation has not been thermally qualified. Complete
the loss/thermal assessment for the final input/load envelope and test the
assembled board. See [TI thermal metrics](https://www.ti.com/lit/an/spra953c/spra953c.pdf).

## Extended margin review — October 27

The [power-margin review](Power-margin-review.md) completes the analytical
capacitor-retention, ripple, feed-forward and loss sensitivities. It includes
inductor rolloff and output-reference corners and excludes invalid CCM cases
for the Eco-mode regulator. The calculated demands narrow the remaining
component/thermal decisions; they do not validate the present capacitors or
cooling layout. Exact part data, final loop selection and the cooling assessment
remain open. No capacitor value, voltage setpoint or PCB geometry changed in
this later calculation-only pass.

## Pi supply relocation — October 27

We moved U41, L2 and their eleven local capacitors/resistors/test header
73.5 mm toward the Pi. The short VIN, SW, FB and divider-ground pattern
is preserved, including its local ground fill/vias. We rerouted input/output,
power-good and neighboring signals, removed the abandoned supply branches,
and routed the output-sense connection around the inductor body. The new
1.5 mm output connection joins the existing distribution tree.

The positive-feed screen at a 3 A Pi allocation improves from 4.8662 to
4.9116 V. This is not a loaded-voltage measurement or full margin approval;
contacts, local returns, heat and regulator dynamics still matter. See
[Power-margin-review.md](Power-margin-review.md) for the tradeoff and limits.
