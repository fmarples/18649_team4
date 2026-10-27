# Ground-plane DC screen — October 27

## Current revision — October 27

The [mounting and encoder revision](Mounting-and-encoder-revision.md) supersedes
older socket, heatsink-placement and encoder-voltage statements below. All
eight supports now meet the 3 mm hole-edge rule; HS80 is installed; encoders
have a separate 4.0 V supply. Current JSON checks carry the active board hash.
Battery/protection, Pi voltage margin and exact capacitor data remain open.

## Earlier review record


We modeled the saved inner ground fill as a resistor sheet. In the cases
with a positive Pi ground offset, the modeled offset is about 2.6–6.5 mV,
compared with the existing 150 mV supply-feed drop at the assumed 3 A load.
This points to the supply feed as the larger loss in this model. It does
not establish the complete return loss or qualify the Pi supply.
No copper, component, BOM or rule changed in this review.

## Model and assumptions

[Ground-plane-check.json](Ground-plane-check.json) records the PCB and load
allocation hashes, all ports and all 18 results. The calculation uses the
saved In1.Cu fill, nominal 15.2 µm copper and resistivity 1.72e-8 Ω·m at
about 20 °C. Each adjacent pair of equal square cells has resistance
`rho / thickness = 1.1316 mΩ`. Copper voids interrupt the mesh edges.

We evaluated 1, 0.5 and 0.25 mm grids, each with 2 and 3 mm current-injection
radii around actual ground vias or plated pads. These broad ports deliberately
exclude the local connector-hole/thermal-spoke scale. SMD returns project
to the nearest ground stitch; this does not prove a dedicated local route.
The longest actual ground-pad projection is 8.19 mm at U81. Tiny resistor
loads use location proxies, up to 10.6 mm away. Multiple return sites share
current equally in this model.

The logic allocation totals 0.716719 A and the 5 V allocation 3.165525 A,
including 3 A at J70. These are design allocations, not measured currents.
Load-ground voltage is compared with the relevant lower feedback resistor's
ground, R431 or R421, because that is the regulator's voltage reference.
We also retain regulator-ground differences in the JSON.

| Case | Additional assumptions |
| --- | --- |
| Output loops only | Logic and 5 V loads return to their regulator grounds; isolates those loops, not a complete vehicle state. |
| Planning | 12 V input, assumed 85% converter efficiency, 0.72 A total motor current and 0.39 A servo current. |
| Stress | 8 V input, assumed 70% efficiency, 2 A total motor current and 4 A servo current; a sensitivity case, not an allowed sustained operating point. |

For the full cases, each buck uses `Iin = Vout × Iout / (Vin × efficiency)`.
Its averaged ground injection is `Iin − Iout`; the battery return extracts
the summed input currents. Motor returns use the two L298 sense-ground pins.
This balances DC current without modeling PWM recirculation or switching.

## Results

Finest grid, 2 mm ports; positive values reduce the voltage available at the load:

| Case | Pi J70 ground minus R421 | Encoder J82 ground minus R431 | CAN U25 ground minus R431 | Pi feed screen minus plane difference |
| --- | ---: | ---: | ---: | ---: |
| Output loops only | +5.680 mV | +3.988 mV | +4.957 mV | 4.8592 V |
| Planning | +2.721 mV | +1.460 mV | +0.579 mV | 4.8621 V |
| Stress | −4.938 mV | −6.368 mV | −12.253 mV | 4.8698 V |

Negative values result from other loads shifting the feedback reference more
than the selected load ground. We do not count this favorable offset as
guaranteed headroom. Across all meshes and ports, the Pi difference spans
−5.603 to +6.545 mV. Neither the sign nor magnitude is a universal limit.

The finest mesh retains 408,170 nodes; 55 disconnected raster fragments are
excluded, and every current port maps to the same retained component.
The largest change in a reported load difference from 0.5 to 0.25 mm is
0.997 mV. The largest current-balance residual is below 6.6e-11 A.
All 200 seeded polygon-membership samples agree with KiCad. Four independent
tests check an analytic rectangular sheet, current/material scaling, a slot
detour, and rejection of disconnected or unbalanced inputs.

These checks establish numerical consistency, not physical accuracy. The
model omits local tracks, barrels, thermal spokes, contacts, hot copper,
outer-layer parallel returns and switching noise. Sub-grid geometry can be
missed. The earlier 50 mV return allowance remains a sensitivity assumption,
not a bound established by this model. The complete supply budget stays open.

## Pi contact allowance

The current [Samtec ESQ catalog](https://suddendocs.samtec.com/catalog_english/esq_th.pdf)
rates an ESQ/TSW pair at 5.7 A per pin with two pins powered; it does not
give the resistance of our ESQ-120-44-L-D mated to the actual Pi header.
The linked [qualification report](https://suddendocs.samtec.com/testreports/2496391_report_rev_1_qua.pdf)
tests ESQ-118-37-L-D with TSW-118-08-L-D, a different pair. We therefore use
the following only as contact-resistance sensitivity assumptions:

| Assumed resistance per mated contact | Loop resistance with two power and eight ground contacts sharing equally | Drop at 3 A |
| --- | ---: | ---: |
| 10 mΩ | 6.25 mΩ | 18.75 mV |
| 20 mΩ | 12.50 mΩ | 37.50 mV |
| 30 mΩ | 18.75 mΩ | 56.25 mV |

The calculation is `Rloop = Rcontact/2 + Rcontact/8`. It omits unequal sharing,
socket tails and Pi copper. For example, subtracting the 20 mΩ/contact case
from the output-loop screen gives 4.8217 V. This is a conditional estimate,
not a measured failure or a manufacturer resistance specification.

## Reproduction

From the repository root, use KiCad's Python to run
`lab4/check_ground_plane.py --solver-python <Python-with-NumPy-SciPy-Shapely>`.
KiCad reads the geometry; the second interpreter solves the sparse network.
Temporary mesh files are removed automatically. Run
`python -m unittest discover -s lab4 -p test_ground_sheet.py` in that second
environment for the four independent checks. The script never writes the PCB.
