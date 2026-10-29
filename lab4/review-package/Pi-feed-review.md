# Pi positive-feed mesh review — October 29

We checked the saved board's entire +5V conductor network rather than one
selected route. This is a DC calculation, not a transient/thermal simulation.
The board and allocation hashes are in [Pi-feed-mesh-check.json](Pi-feed-mesh-check.json).
No placement, routing, net or BOM change resulted from this review.

## Model and result

`check_pi_feed.py` extracts pad/track/filled-zone polygons through KiCad.
It meshes each copper layer and connects plated holes with four barrel
sectors. The inputs are the saved 35/15.2/15.2/35 µm copper stack, assumed
20 µm barrel plating and 20 °C copper resistivity of 1.72e-8 ohm-metres.
Loads are the existing allocation, including 3 A at J70 pin 4. Current enters
at L2's output pad and leaves through the actual load-pad regions; J70's
port is on the back layer where the underside socket is installed.

| Mesh cell | Nodes | Calculated Pi positive-feed drop | Total +5V copper loss |
| --- | ---: | ---: | ---: |
| 0.10 mm | 99,824 | 69.12 mV | 0.2189 W |
| 0.05 mm | 400,591 | 68.03 mV | 0.2154 W |

Refining the grid changed the Pi result by 1.09 mV (1.6%). Kirchhoff current
balance residuals were below 1 nA; source work and resistor dissipation agree.
Independent tests reproduce a known parallel/series circuit, a rectangular
sheet and current scaling; disconnected energized networks are rejected.
This is a numerical consistency check, not a bound on all model error.
Uniform pad-current injection and four-sector barrels approximate current
spreading. Actual plating/thickness, lead resistance, temperature, contacts,
ground return, switching behavior and regulator accuracy are outside this model.

With the earlier 5.014644 V source minimum, the finer mesh gives 4.9466 V
before the omitted losses. Using the same **assumed** 80 °C copper, 10 mΩ
per mated contact, seven equally sharing grounds and 20 mV return allowance
gives about 4.8763 V. That leaves only 14.8 mV above the 4.8615 V upper
undervoltage-detector corner, before transients and omitted socket-lead loss.
The detector corner is not a guaranteed minimum operating voltage. The mesh
does not close the existing supply-margin issue.

## Evaluated changes

A separate working copy added a local +5V back-layer pour between the regulator
area and Pi. Its 0.10/0.05 mm meshes gave 57.07/56.33 mV: an improvement of
about 11.7 mV at the finer grid. Native DRC found zero unconnected items and
no electrical-clearance findings; its 19 findings were missing custom-library
configuration in the scratch directory. This trial was **not applied**. It
removes some outer ground copper and does not by itself establish enough
transient margin; adopting it would require return-path and export rechecks.

We also checked TPS564247 as an alternative to TPS564252. It retains ±1.5%
full-temperature reference tolerance, and pin 4 is AGND rather than PG, so
it is not an unmodified drop-in improvement. See the manufacturer
[TPS564247](https://www.ti.com/lit/ds/symlink/tps564247.pdf) and
[TPS564252](https://www.ti.com/lit/ds/symlink/tps564252.pdf) specifications.
Raising the feedback setpoint alone would spend the remaining high-voltage
and load-release margin; we did not change it without a complete budget.

The necessary next electrical decision is the Pi supply's complete
startup/load-step and high/low-voltage envelope, followed by an appropriate
power-path/regulator revision if that envelope cannot be met. TI's available
encrypted PSpice model has not been run in the available KiCad/ngspice setup.
Neither a guessed response time nor a generic efficiency number closes this
review. Hardware voltage and temperature checks still belong to prototype
bring-up; no new chassis measurements are requested.

## Additional October 29 evidence

A second scratch-board trial placed local +5V pours on both B.Cu and In2.Cu
over x=74–113 mm, y=126–176 mm. At the same 0.10 mm mesh, the drop was
53.78 mV versus 69.12 mV on the saved design. Native DRC had no electrical
or unconnected findings; five scratch-library warnings remained. We did
not adopt the trial: it removes ground copper, needs a return-path review,
and approximately 15 mV improvement does not settle the startup or thermal
question. The trial is not part of the fabrication exports.

The [official Pi documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
lists a recommended 3 A supply and approximately 600 mA typical bare-board
current. Its dated 2019 Pi 4 measurements show about 850 mA maximum during
boot and 1.25 A during its stress workload. Those are useful workload
examples, not guaranteed maxima for every software revision and workload.
The confirmed application has no additional USB/camera/display/fan loads.
We therefore distinguish likely operation from the retained 3 A design
stress case; we have not lowered that case merely to obtain a passing result.

TI's TPS564252 model release 1.00 (April 10, 2023), supplied for PSpice
17.4, explicitly excludes temperature behavior, quiescent/shutdown current
and output UVP/OVP. It models startup and several control/current-limit
functions, but running it would not qualify PCB cooling or every fault mode.
No compatible PSpice installation is available here and no simulated result
is claimed. Source: the feature document accompanying the
[TI model download](https://www.ti.com/product/TPS564252).

The next useful external input is an electrical review of the actual
5.1 V supply and intended sustained/peak workload, not another chassis
measurement. That review must either support the chosen prototype envelope
or identify the necessary regulator/power-path change. Physical transient
and temperature validation belongs to the assembled prototype.

## Reproduce

Extract with KiCad's Python; then solve with a Python environment containing
NumPy, SciPy and Shapely. Put the intermediate geometry outside the repository.

```text
python check_pi_feed.py extract --geometry /temporary/pi-feed.json
python check_pi_feed.py solve --geometry /temporary/pi-feed.json
python -m unittest test_pi_feed.py
```

The first command reads the saved copper. The second includes parallel
current paths and reports two grid resolutions. The last checks the circuit
solver against independent analytical cases. None modifies the PCB.
