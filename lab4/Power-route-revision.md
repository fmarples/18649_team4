# Power copper and package correction — October 28

We widened 779 existing power-track segments where saved clearances allowed.
Their IDs, endpoints, layers and nets are unchanged. We preserved the ground
thermal-spoke area at C400 rather than crowding it with wider positive copper.
The battery, protected input, regulated supplies and motor branches now lose
less voltage in the checked routes. No component current rating follows from
track width alone. [Semantic comparison](Power-route-revision-check.json).

| Positive path | Previous resistance | Revised resistance |
| --- | ---: | ---: |
| J40.1 to F1.1 | 5.415 mΩ | 4.332 mΩ |
| F1.2 to Q1.2 | 6.265 mΩ | 4.822 mΩ |
| Q1.3 to L298 supply U80.4 | 43.267 mΩ | 32.374 mΩ |
| Q1.3 to servo converter U40.1 | 103.249 mΩ | 92.394 mΩ |
| Q1.3 to 5 V converter U41.1 | 64.972 mΩ | 56.681 mΩ |
| Q1.3 to logic converter U42.1 | 76.530 mΩ | 66.126 mΩ |

These are nominal 20 °C predecessor-path screens, counting whole track items
and nominal plated vias. They omit parallel paths, pad spreading and contact
resistance; they are not measured or guaranteed worst-case resistances. The
previously improved L2-to-Pi path remains 23.000 mΩ.

We also found a package mismatch. Panasonic EEU-FR1E471 (C802) has a 10 mm
body, 12.5 mm body length and 5 mm lead spacing. Its former D8/P3.5 footprint
was too small. We changed the schematic, PCB and BOM views to D10/P5 and moved
the positive-pad origin 1.5 mm left. The ground pad stays at (104.85, 47) mm;
both pads contact their intended copper. All other footprint positions and
the selected mounting pattern are unchanged. The enlarged body clears the
heatsink and surrounding courtyards. See [package review](Critical-package-review.md).

The new [load-allocation report](Load-allocation-check.json) includes battery
input and complete-feed Pi sensitivity cases. A buck's input current is
output power divided by local input voltage and efficiency; adding output
amperes across different rails is incorrect. We iterate the converter input
voltage to include shared input-track drops. See [power margins](Power-margin-review.md)
for the stated assumptions and unresolved operating margins.

Fresh native checks report zero ERC, DRC, schematic-parity and unconnected
findings. All 331 targeted connections pass; the critical-package audit now
covers 41 components. The detailed four-layer physical stack is also stored
in the PCB. This revision is checked design progress, not fabrication release.
