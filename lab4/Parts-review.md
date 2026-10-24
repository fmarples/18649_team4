# Parts and physical interface review

24 October 2026. We reconciled the design with the course's
[v3 stock-list reply](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792789284321879).
Tom says it lists the parts on hand, excluding front current-sensing additions
and standoffs. [Course-stock-v3.csv](Course-stock-v3.csv) records its 52 named
parts and generic headers. Local stock does not establish quantities or JLCPCB stock.

## Documented selections

- The list includes SN65HVD231DR, SK520B, L298N, GCT SWT0210-045026GSA and Boyd
  6396BG. The exact listed MPNs no longer need teammate confirmation.
- Servo shunt R1 is Vishay WSL2512R0100FEA: 10 mΩ, 1 W, 1%. Its local footprint
  follows [Vishay document 30100, page 2](https://www.vishay.com/docs/30100/wsl.pdf):
  two 1.65 × 3.68 mm pads with a 4.06 mm inner gap. Dissipation at the proposed
  4 A allocation is 0.16 W; this does not prove the converter/servo supports 4 A.
  Kelvin sense routing remains necessary.
- DF63A-1618SC contacts are for 16–18 AWG; DF63A-2022SC is the 20–22 AWG servo
  adapter candidate. The family name does not establish that existing vehicle
  plugs mate with our headers. Wire, contact and crimp tool must match.
- D40 is explicitly Diotec BZT52C12 in SOD-123F; its assigned footprint is
  SOD-123F. The lamp transistor now has the full MMBT3904-7-F ordering code.
  F1 identifies the Keystone 3568 holder. Littelfuse 0297010.L is now the
  separately listed **review candidate** fuse; qualification is described below.
- Manufacturer/source fields are filled for placed named circuit parts.
  Exact stock must be checked when ordering. The 75 kΩ 0.1% and 22 kΩ resistor
  listings need an availability/substitute check; preserve feedback tolerances.

## Selected battery and charger

We selected Tenergy 11609 and charger 01025 as our design/BOM baseline.
Dantona CMP-AA-21-37 is retained only as a historical comparison, with zero
requested quantity; its maximum discharge current was not established. The selected pack,
[Tenergy 11609](https://power.tenergy.com/at-tenergy-12v-4200mah-nimh-rechargeable-battery-pack-10s1p-50-4wh-30a-rate/),
uses ten **Sub-C**, not AA, NiMH cells: 12 V / 4.2 Ah, manufacturer-stated 30 A
continuous discharge, 115 × 44.4 × 46.76 mm, approximately 1.3 lb. Listed
build-to-order lead time is 3–7 business days; verify at purchase.

Tenergy lists [01025](https://power.tenergy.com/tenergy-smart-universal-charger-for-nimh-nicd-battery-packs-6v-12v-ul/)
as compatible: NiMH/NiCd, 5–10 cells, selectable 1/2 A, negative-delta-V
termination. Supplied Tamiya/clip leads do not mate directly with our Hirose
connector. A keyed, correctly polarized adapter is needed. This recommendation
now accompanies the selected 11609 pack. Neither item has been ordered.
On October 23 the manufacturer lists $118.99 for the pack and $26.69 for the
charger, or $145.68 before tax/shipping and adapters. Purchasing and delivery
remain to be confirmed; the design selection is not an order.

The team reported a cardboard-envelope check on October 24: a
115 × 50 × 50 mm stand-in fits between the existing chassis plates, with
approximately 51.75 mm usable vertical space. This supports the selected
115 × 44.4 × 46.76 mm pack fitting in that location. With 46.76 mm vertical,
the calculated gross height allowance is 51.75 - 46.76 = 4.99 mm; the 50 mm
stand-in leaves about 1.75 mm. These are allowances before fastening material,
protruding hardware and local cable interference, not measured final clearances.
The pack itself has not been installed. Finalize its retaining strap and lead/
connector route; the cardboard size check does not need repeating.
A larger-current pack does not raise the L298's limits. Only 11609 and 01025
are requested in the purchasing list.

## Open package and mechanical checks

The [Boyd 6396BG drawing](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Cooling-High-Power-Extruded-6390.pdf)
specifies 41.91 × 25.4 × 25.4 mm. The old 28 × 16 mm reservation was too small.
We updated the drawing envelope, but it is not a validated installation.
Boyd lists TO-218/TO-220 compatibility; L298N is Multiwatt-15. Verify the hole,
tab contact, mounting hardware and orientation on the actual course parts.
Final clearance and thermal performance depend on that installation. Electrical
DRC does not check an unattached heatsink.

The exact GCT drawing has been located, but contact pairing and recommended
pads have not been visually verified. Five switch footprints remain unassigned;
we have not substituted an arbitrary 4.5 mm switch.

Physical checks still needed: original motor/encoder/servo plug shapes, pin
order and wire gauges; actual encoder supply/output type; heatsink fit;
the battery retaining strap/lead route; and the proposed Pi/chassis vertical
spacer stack. The battery envelope has passed the team's cardboard check.
The four chassis center positions and 4.5 mm diameters are already established.

## External hardware selected for review

The purchasing BOM now itemizes these parts instead of assigning anonymous
hardware selection to the team. Quantities below include spares and mean
individual pieces, except where wire length is stated. Supplier pack sizes,
stock, cost and lead time must be checked before an order; none is reserved.
The 22mm Pi spacer is catalog-listed, but its price/MOQ/lead time is not published.

| Use | Selected part/specification | Installed + spare | Reason and remaining fit check |
|---|---|---|---|
| Isolation/termination/recovery caps | [Samtec SNT-100-BK-T-H](https://www.samtec.com/products/snt-100-bk-t-h) | 18 + 2 | 2.54mm pitch, handle for removal. Twelve isolation + four termination caps installed normally; two BOOT0 recovery caps stored off-board. Check adjacent-cap access. |
| Chassis spacers | [Wurth 970350365](https://www.we-online.com/components/products/datasheet/970350365.pdf) | 4 + 1 | M3 female/female, 35mm body, nylon, 6mm across flats. Preserves proposed board height; verify smooth chassis holes and access underneath. |
| Chassis screws | [RS PRO 190434](https://us.rs-online.com/product/rs-pro/190434/70790858/) | 8 + 2 | M3x8, one screw into each end of each spacer. Confirm plate thickness and thread engagement. |
| Chassis washers | [RS PRO 4832592](https://us.rs-online.com/product/rs-pro/4832592/70823582/) | 8 + 2 | 3.2mm ID, 7mm OD, 0.5mm thick. Under screw heads; lower washer bridges the measured 4.5mm chassis hole. |
| Pi spacers | [OneMonroe/Lyntron AA5069-2545-22.0-00](https://catalog.onemonroehardware.com/item/lyntron-standoffs/metric-female-standoffs/aa5069-2545-22-0-00) | 4 + 1 | M2.5 female/female, 22mm body, 4.5mm round OD. Fits the proposed <=5mm hardware envelope; actual socket engagement remains untested. |
| Pi screws | [Aspen ME031-25045X6](https://www.aspenfasteners.com/content/2D_PDF/product61/ME031-25045X6.PDF) | 8 + 2 | M2.5x6, pan head up to 5mm. No spacing washers; verify adjacent components and thread depth. |
| Encoder housings | [Harwin M20-1060400](https://www.harwin.com/products/M20-1060400) | 2 + 1 | Four-position 2.54mm female housing for 0.64mm square pins; not keyed, so mark pin 1. |
| Encoder contacts | [Harwin M20-1180046](https://cdn.harwin.com/pdfs/IS-15.pdf) | 8 + 4 | Loose tin contacts, 22-30AWG. Requires matching crimp tooling and wire dimensions. |
| Servo adapter donor | [Pololu 2184](https://www.pololu.com/product/2184) | 1 + 1 | 300mm JR/Futaba male-female extension, documented 22AWG wire. Retain the servo-mating male end. |
| Charger housing | [Hirose DF63A-2EP-3.96C](https://www.hirose.com/en/product/p/CL0680-0535-5-00) | 1 + 1 | Inline mating plug for the battery socket; distinguish it from the board header. |
| Charger contacts | [Hirose DF63-2022PC](https://www.hirose.com/en/product/p/CL0680-0539-6-00) | 2 + 2 | 20-22AWG male contacts for the 1/2A charging adapter, not the vehicle supply cable. |

The chassis stack is screw head / washer / PCB / 35mm spacer / chassis /
washer / lower screw head. Washers do not add to the 35mm board-to-chassis gap.
With a 1.6mm PCB and 0.5mm washer, an 8mm top screw engages about 5.9mm of
the spacer's 10mm thread depth. Actual lower engagement depends on plate
thickness. This assumes a clearance hole, not a screw forced into unmatched
chassis threads. The Pi stack uses 22mm spacers and approximately 4.4mm screw
engagement through a 1.6mm board; the selected connector and actual board
thicknesses still need a dry fit. Equal spacer heights matter for the 40-pin socket.

## Harness definition

We retain the board pin definitions in [Actuator-design.md](Actuator-design.md).
The [identified motor specification](../doc/HARDWARE.md)
already gives PH2.0-6PIN and encoder supply 3.3-5V; its cable cavity order is
not documented there. Thus connector family research is done, but cable
continuity still needs checking. The schematic's nominal 5.1V encoder supply
also exceeds that published 5V upper value: the encoder supply voltage must
be corrected or supported by better manufacturer evidence before connection.

- **Motor/encoder:** reuse the two existing six-wire motor cables. Course v3
  also lists DFRobot FIT0587 donor cables; request two plus one spare only if
  needed, after checking the physical mating plug. Separate the two motor
  leads to DF63-2S-3.96C and the four encoder signals to M20-1060400. Do not
  infer cavity numbers or polarity from wire colors.
- **Battery:** DF63-2S-3.96C socket, pin 1 positive / pin 2 ground, with
  DF63A-1618SC contacts and specified 16AWG adapter wire. Do not insert an
  undersized original motor wire into a 16-18AWG crimp; use an appropriately
  insulated transition if needed. The connector on a live battery must not
  leave bare conductors exposed.
- **Charger:** preserve the supplied adapter's Tamiya mating end and replace
  its clip end with DF63A-2EP-3.96C, using DF63-2022PC contacts on 22AWG wire.
  If the supplied lead is another size, use a correctly made transition,
  rather than an incompatible crimp. Verify positive-to-positive continuity
  with charger and pack disconnected. Charge the disconnected pack, not the PCB.
- **Servo:** retain the Pololu2184 male end that mates with the servo. Replace
  the other end with DF63-3S-3.96C and DF63A-2022SC contacts, wired to J90:
  1=GND, 2=sensed6.6V, 3=PWM. The 22AWG donor does not prove the original
  servo plug can carry the provisional 4A allocation continuously.
- **Wire:** request cut lengths of [Alpha3057](https://www.alphawire.com/products/wire/hook-up-wire/premium/3057)
  stranded16AWG (3m red +3m black, including spare/routing allowance) and
  [Alpha3051](https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=3051)
  stranded22AWG (1m red +1m black for charging). Equivalent documented lab
  wire avoids buying whole reels. Wire gauge is not a universal ampacity:
  final routing, insulation, bundling, length and temperature enter the check.

Contact models and wire ranges are selected; verify access to compatible
crimp tools or purchased precrimp leads before buying loose terminals. We
have not assumed a generic crimper produces a qualified Hirose connection.

## Fuse candidate and limits of the calculation

We propose **Littelfuse0297010.L, 10A MINI, 32VDC**, one installed and two
spares, for review. [Keystone3568](https://www.keyelco.com/product.cfm/product_id/306)
explicitly accepts Littelfuse297 and is rated30A; the battery header is rated14A.
These component ratings do not establish the rating of the entire assembled path.

Using the existing output allocations, the regulated branches total
`6.6*4 + 5.1*3.3 + 3.318*0.8 = 45.8844W`.
At assumed85% conversion efficiency, input current is `P/(0.85*Vpack)`.
Adding the published0.36A rated-current value for each motor gives:

| Screening case | Calculated pack current |
|---|---:|
| 12V nominal, allocated regulated loads +0.72A motors | 5.22A |
| 8V electrical design-envelope endpoint, same assumed currents | 7.47A |
| 12V, regulated allocations +6.4A raw two-motor stall sum | 10.90A |

These are mixed planning scenarios, not measured averages or an operating
guarantee. In particular,0.36A is not a bound on driving current, motor current
does not stay fixed as voltage/load changes,85% is assumed, and8V is not a
selected NiMH discharge cutoff. The stall row exceeds the L298 limits and
does not authorize that operation. This screening supports a10A candidate
over7.5A but cannot finalize the fuse.

The [Littelfuse297 datasheet](https://www.littelfuse.com/assetdocs/littelfuse_datasheet_297_mini32v.pdf?assetguid=42c9dd21-a88e-4328-8e67-2f832444faf1)
gives typical allowed continuous loads of8.6A at40C and8.0A at60C for the10A
part. At twice rated current, opening can take0.15-5s. A10A label therefore
does not mean current is clamped to10A. Final qualification needs the
measured normal/startup profile, ambient, all wire/connector/PCB-path ratings
and their tolerance of the fuse's clearing interval. Check smaller branch
wiring separately. The main fuse does not protect each L298 bridge at2A,
and a fuse mounted on the PCB does not protect the upstream battery lead.

## Vehicle LEDs and heatsink hardware

We now list one installed plus one spare of each color:
[WP7113ID red](https://www.kingbrightusa.com/images/catalog/SPEC/WP7113ID.pdf),
[WP7113QWC/D white](https://www.kingbrightusa.com/images/catalog/SPEC/WP7113QWC-D.pdf),
[WP7113YD yellow](https://www.kingbrightusa.com/images/catalog/SPEC/WP7113YD.pdf),
and [WP7113QBC/D blue](https://www.kingbrightusa.com/images/catalog/spec/wp7113qbc-d.pdf).
These are documented replacements, not claims about the LEDs already installed.
With5.1V,220ohms and an assumed0.2V transistor drop, typical published forward
voltages give roughly7-14mA. Existing compatible lamps can be reused; do not
order duplicates simply because the BOM includes a fallback.

**One purchasing selection remains genuinely unresolved: the heatsink
attachment/interface.** Boyd6396BG is course-listed, but its published package
list is TO-218/TO-220; our L298N is Multiwatt15. We have not treated a generic
TO-220 mounting kit as a verified fit. The team needs to show the course
heatsink/tab mounting arrangement or obtain the staff's intended attachment;
then the screw length, nut and thermal interface can be selected. This is a
specific geometry question, not a request for the team to research the whole BOM.

No purchases or fabrication release have been made. The active board BOM
remains [BOM-Hand-assembly.csv](BOM-Hand-assembly.csv); all changes above are
off-board purchasing specifications and do not change the circuit netlist.
