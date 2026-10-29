# Mounting clearance and encoder supply — October 27

We applied the user's 3 mm hole-edge rule to every chassis/Pi support,
including copper that a screw head or standoff could touch. The
[course reply](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793125271438699)
notes this copper-contact concern. No exception is assumed for the Pi.

## Mounting and Pi connection

H1–H4 have 3.2 mm drills and a 4.60 mm clear radius from their centers.
H5–H8 have 2.7 mm drills and a 4.35 mm clear radius. The holes themselves
are non-plated. Thirty-two rule areas exclude tracks/vias/pours, and an
independent check also tests electrical pads and component courtyards.
All eight hole centers stay at the previously checked positions.

The original ESQ-120 socket was only 1.995 mm from the nearest Pi hole edge.
We selected **ESQ-118-44-L-D**, a 36-contact version covering physical pins
3–38. Its 46.23 × 4.95 mm body is **4.535 mm** from the nearest hole edge,
exceeding the rule by 1.535 mm. A 5.5 mm maximum screw/washer/standoff outside
diameter leaves 3.135 mm to the body. The nominal 22 mm Pi gap and 18.67 mm
socket body give 5.17 mm insertion, within the 3.68–6.35 mm catalog interval.
These are drawing-based dimensions, not an assembled fit test.

Pins 1/2/39/40 are omitted; all used signals remain. **Pin 4 alone carries
5 V.** Ground uses the retained ground pins. The library pad numbers retain
Pi physical numbering to prevent a silent two-pin shift. The bottom silk,
schematic and fit template identify the correct alignment. Select hand
soldering according to the exact Samtec process guidance; the catalog's
5.7 A/contact ESQ/TSW test is not a rating of the assembled Pi interface.
Mouser listed only one available against two requested including a spare;
stock and delivery are not reserved. Reconcile this substitution before ordering.

Sources: [Samtec catalog](https://suddendocs.samtec.com/catalog_english/esw_th.pdf),
[part drawing](https://suddendocs.samtec.com/prints/esq-sdt.pdf),
[Mouser exact variant](https://www.mouser.co.uk/en/ProductDetail/Samtec/ESQ-118-44-L-D?qs=PB6%2FjmICvI2MYbzEyjh0rw%3D%3D).

## Heatsink installation

HS80 is the **6396BG straight-pin** footprint, with two 2.89 mm finished
plated holes, 4.5 mm pads and 25.4 mm center spacing. Its anchors are at
(62.30, 53.975) and (87.70, 53.975) mm in KiCad coordinates. U80 moved
(+3, −3) mm; C800/C802/J80 moved to clear the fins and web. All affected
connections are restored. The only courtyard exception is the intentional
U80/HS80 clamp relationship; other courtyard checks remain enabled.

The fin/web envelope has 0.5 mm component clearance and 0.2 mm top-copper
clearance. Anchors are intentional ground-connected mechanical contacts;
they are not the motor-current return path. Do not rely on anodizing for
insulation. The M3 screw/nut/washer/grease specification and assembly sequence
are in [Heatsink-mounting-review.md](Heatsink-mounting-review.md).
The input copper near J81's locating hole has a short 1.38 mm neck instead
of 1.50 mm; current/thermal review must retain that local restriction.
Mounting geometry does not qualify L298 stall operation or temperature.

## Encoder supply correction

The previous 3.3 V feed could reach about 3.17 V in the stated allocation
screen, below the recorded encoder range of 3.3–5 V. We added **U82,
MCP1700-4002E/TO**, from the 5.1 V rail, with **C804/C805,
TPSB106K016R0800**, 10 µF, 16 V, ±10% tantalum capacitors. The positive
terminal is pad 1. Their 0.8 ohm maximum ESR at the specified catalog test
condition supports the LDO's 0–2 ohm requirement; this is not an all-temperature
ESR guarantee. The input and output capacitors each exceed its 1 µF minimum.

U82's TO-92 pins are 1 ground, 2 input and 3 output. The wide inline footprint
requires forming its leads to 2.54 mm pitch. J82/J83 pin 1 now receives 4.0 V;
U81 and R804–R807 remain at 3.3 V. The LVC14A accepts input signals up to
5.5 V, so the encoder supply does not raise MCU logic levels.

At the assumed 20 mA per encoder, a deliberately additive reference/load/line
screen gives 3.796–4.204 V at U82. Positive routing drops are 3.918 and
1.935 mV, giving 3.792 and 3.794 V at the connectors before ground/transient
losses. The dropout screen leaves 0.304 V after reserving 0.350 V dropout.
The thermal calculation gives 0.0582 W and about 7.7 °C rise using the
131.9 °C/W datasheet model. None of these is a measurement of our encoders
or PCB. The 40 mA allocation is well below the regulator's 250 mA rating.

Sources: [Microchip MCP1700](https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP1700-Data-Sheet-20001826F.pdf),
[AVX TPS series](https://datasheets.kyocera-avx.com/TPS.pdf),
[DigiKey U82](https://www.digikey.com/en/products/detail/microchip-technology/MCP1700-4002E-TO/2614904),
[DigiKey capacitors](https://www.digikey.com/en/products/detail/kyocera-avx/TPSB106K016R0800/678477).
The BOM requests two U82 and three capacitors including spares, less any
confirmed course allocation. These parts were absent from the October 26
purchasing snapshot.

## Verification and remaining limits

[Mounting-clearance-check.json](Mounting-clearance-check.json) checks all eight
holes; [Heatsink-mounting-check.json](Heatsink-mounting-check.json) checks the
installed anchors and fin/web space. Placement, pin-map, routing, supply,
ground-plane, solder-via, CAN/reference and package checks were refreshed.
The full native audit is recorded in [Fabrication-check.json](Fabrication-check.json).

The subsequent 5 V regulator relocation improves the Pi positive-feed screen
from **4.8662 to 4.9116 V at 3 A**, before contact, local-ground, regulator
dynamic and heating losses. Its upper low-voltage warning-threshold corner
is 4.8615 V; that threshold is not a guaranteed operating specification.
The rerouted candidate passes native DRC. Final battery/input and load
assumptions are still needed for full power qualification. Exact selected
buck-capacitor bias/aging data remain unavailable. Published typical models
for two unselected alternatives are compared in
[Power-margin-review.md](Power-margin-review.md); neither is qualified by
that comparison alone.

Further release work therefore needs the final battery/charger and motor
fault expectations, a defensible Pi load/voltage budget, capacitor data or a
qualified substitution, and procurement/interface decisions. Physical mating,
fastener retention, continuity and powered testing belong to assembly.
