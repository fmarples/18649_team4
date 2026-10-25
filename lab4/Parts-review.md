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
  Exact stock must be checked when ordering. The original 75 kΩ and 22 kΩ resistor listings are out of stock.
  Documented alternatives are listed below; preserve feedback tolerances.

## Supplier check, October 24 evening

We use course stock first. All new non-battery purchases must use DigiKey or
Mouser. The [20:09 EDT course reply](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792886971109979)
limits Amazon to batteries; a possible connector or charger exception would
need a separate TA decision. We have not applied such an exception.

We checked every supplier field in both active BOMs. In Preliminary-BOM.csv,
93 rows link only to DigiKey, one provisional battery row links to Amazon,
25 generic-header rows request course stock,
two unresolved rows have no purchase link (charger and heatsink attachment),
and six zero-quantity rows are references only. The 96-row hand-assembly BOM
has 71 DigiKey-linked rows and the same 25 course-stock header rows.
These counts describe sourcing documentation, not 127 qualified purchases.

- We replaced manufacturer-only links for J40/J80/J81, J90, U81 and the four
  lamp transistors with exact-MPN DigiKey listings. No part, footprint or
  quantity changed. U81 SN74LVC14APWR is out of stock on the checked listing;
  the reviewed SN74LVC14APW carrier alternative below now resolves its source.
- The Amazon generic-header link came from the course's v3 list. We removed
  it from the active purchasing fields and retained the original course list
  as evidence. Confirm course quantities and row/pin dimensions; any shortage
  must be sourced through DigiKey/Mouser, with a replacement MPN selected.
- The 16AWG and 22AWG wire rows now link to DigiKey's exact Alpha Wire
  RD005/BK005 spool listings. Our requests are still cut lengths in metres.
  Those listings sell 100ft spools; do not interpret 6m or 2m as spool counts.
  Use lab cut lengths first, or reconcile order units and cost before buying.
- Manufacturer datasheets and zero-quantity research alternatives remain
  technical references. LCSC fields and BOM-JLC-hybrid.csv are historical
  assembly comparisons, not the active purchasing route.

Supplier compliance does not establish stock availability, cable compatibility,
or current capability. Battery/charger selection, servo-lead qualification,
course quantities and deferred attachment hardware remain explicit open items.

## TA review notes in the purchasing BOM

The `TA_review` column in Preliminary-BOM.csv now identifies the requested
follow-up directly beside each affected item. Existing `Status` and
`Stock_status` notes still apply; a blank review cell does not certify a part.

- **Course-stock quantities:** the v3 list identifies parts, but does not
  publish the quantities allocated to us. The affected rows ask the TA to
  confirm how many of `Requested_total` the course can supply. That column
  includes proposed spares; it is total demand, not an additional purchase
  on top of course stock. Buy only the shortfall through DigiKey/Mouser.
  Generic headers also need the stated row/pin dimensions. This cannot be
  closed by reading a distributor's inventory.
- **Servo lead:** the unresolved adapter row asks for a course-stock or
  DigiKey/Mouser male lead suitable for the LD-1501MG. SparkFun19224 remains
  a candidate because the reviewed documentation gives no contact/cable
  current rating for the 2.4-3A servo stall range. The focused question is in
  the BOM itself. Physical fit, polarity, continuity, retention, voltage drop
  and heating checks occur before powered use; they are not claimed complete.
- **U81 source resolved:** use [SN74LVC14APW, DigiKey 296-26584-5-ND](https://www.digikey.com/en/products/detail/texas-instruments/SN74LVC14APW/1591867)
  as the reviewed procurement alternative to SN74LVC14APWR. [TI's carrier-options table](https://www.ti.com/product/SN74LVC14A/part-details/SN74LVC14APWR)
  identifies them as the same product supplied in different carriers. Both
  use PW/TSSOP-14; the tube option needs no circuit or footprint change for
  our team-assembly plan. DigiKey showed 291 available at $1.05 each on
  October 24. Request **two individual ICs total: one installed plus one
  spare**, not both ordering codes or an entire 90-piece tube. The BOM retains
  the schematic's PWR identifier and explicitly records PW as the purchasing
  alternative. Recheck stock when ordering and record the fitted ordering code.

## Battery and charger: provisional review basis

The [October 24 purchasing rule](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792870041277289)
requires DigiKey or Mouser for parts outside the course list. The
[battery-only Amazon exception](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792878299024869)
asks for Pittsburgh delivery, preferably Prime one- or two-day delivery.
In the October 24 evening DMs, Anson said the proposed Tenergy pair should
work and allowed somewhat longer delivery. Ayaan allowed us to submit the
provisional design tonight, identify the unresolved battery, and find a
replacement within the next week. These replies remove final battery
selection as a prerequisite to tonight's review; they do not place an order.
We keep all new non-battery purchases, including the charger, on DigiKey/Mouser.
Tenergy 11609/01025 remain zero-quantity design references. We identify one
provisional Amazon pack below; a qualified pack/charger pair remains unresolved.

We added the team's [Tenergy Amazon candidate, ASIN B077Y9HNTF](https://www.amazon.com/dp/B077Y9HNTF)
to the existing one-pack BOM request for review, without adding a second battery.
The supplied short link, https://a.co/d/0gL86VSB, resolves to this listing.
It specifies 12V, 2000mAh NiMH and **2A maximum continuous discharge (1C)**.
We found no documented 10A pulse rating or permitted duration. Its 2A limit is
already below our assumed **2.883A battery-input planning case** in
[Current-evidence.md](Current-evidence.md); that case is not measured consumption.
The issue is a published continuous-current limit, not simply missing certification.
We have not qualified this candidate for full-vehicle operation or purchase.

The listing's 73.5x53.5x30.5mm dimensions are outside the checked
115x50x50mm envelope in an axis-aligned orientation; the reported 51.75mm
usable height is also less than 53.5mm. A different mounting arrangement
would need checking. The title says bare leads while its specification table
says Hitec, so the supplied lead end must be confirmed. The corresponding
[Tenergy 11606 manufacturer page](https://power.tenergy.com/tenergy-nimh-12v-2000mah-battery-pack-w-bare-leads/)
lists the same electrical limits and dimensions with bare leads. We use the
verified ASIN as the BOM identifier because the Amazon-to-MPN mapping is not
explicit. The manufacturer's recommended maximum charging current is 1A;
do not transfer the older 4.2Ah reference pack's 2A charging setting to this pack.
The exact charger, permitted supplier, delivery and final pack choice remain open.

The earlier [Tenergy 11609](https://power.tenergy.com/at-tenergy-12v-4200mah-nimh-rechargeable-battery-pack-10s1p-50-4wh-30a-rate/)
reference is ten Sub-C NiMH cells, 12V/4.2Ah, stated 30A continuous discharge,
115x44.4x46.76mm. Its manufacturer lists
[01025](https://power.tenergy.com/tenergy-smart-universal-charger-for-nimh-nicd-battery-packs-6v-12v-ul/)
as compatible. The pack is listed at $118.99 with a 3-7-business-day build
time before shipping; the charger is listed at $26.69. Prices were checked
October 24 and are not reserved. We have not verified an Amazon listing for
this exact pack or a permitted source for the charger. Its build time does
not establish delivery by the layout deadline.

The [01025 manual](https://power.tenergy.com/content/manuals/01025_manual.pdf)
supports 5-10 NiMH cells, 1000-9000mAh and selectable 1A/2A charging with
negative-delta-V termination and a temperature sensor. The pack's documented
2A rapid-charge limit matches the charger's 2A setting. A correctly polarized
adapter and disconnected-pack charging are still required. We prefer this
documented pair if a permitted purchasing route and acceptable delivery can
be established; compatibility alone does not close procurement.

Additional candidates screened on October 24:

| Candidate | Published specification | Disposition |
|---|---|---|
| [Tenergy 11660](https://power.tenergy.com/at-tenergy-12v-3800mah-nimh-rechargeable-battery-pack-10s1p-45-6wh-10a-rate/) | 12V NiMH, 3.8Ah, 10A continuous; 95x67x40mm; $85.99, built to order | Does not fit the measured 115x50x50mm envelope in an axis-aligned orientation. A different mounting envelope and permitted source would be needed. |
| [Tenergy 11606](https://power.tenergy.com/tenergy-nimh-12v-2000mah-battery-pack-w-bare-leads/) | 12V NiMH, 2Ah; 2A maximum continuous; 73.5x53.5x30.5mm | Corresponding manufacturer reference for the provisional Amazon candidate above. Below the 2.883A planning case; 10A pulse capability and installed fit are unverified. |
| [CNHL S220403BK shorty](https://chinahobbyline.com/products/cnhl-black-series-shorty-2200mah-3s-11-1v-40c-lipo-battery-with-xt60-plug) | 3S LiPo, 11.1V nominal/12.6V full, 2.2Ah, advertised 40C continuous; 77x33x26mm; XT60 and JST-XH balance lead | Fits the envelope by published dimensions, including the manufacturer's stated 1-5mm dimensional variation. Alternative only: changes the selected chemistry and requires lithium charging/cutoff provisions. |

For the CNHL alternative, 40C x 2.2Ah = 88A is the manufacturer's advertised
continuous rating, not our measured capability or our circuit's rating. The
[Amazon listing candidate B0DQP7SKGV](https://www.amazon.com/dp/B0DQP7SKGV)
could not be read directly, so exact variant, seller, current price and
Pittsburgh delivery remain unverified. We have not added it to the purchase
quantities. The handout's lithium option requires balance charging and a
low-voltage cutoff; these are not implemented by changing a BOM line.
A [SkyRC e3](https://www.skyrc.com/Charger/Multi-Channel/e3_Charger?order=ASC&sort=p.price)
is a documented 2-3S LiPo balance-charger candidate, but its permitted
procurement route is also unverified. Never use the NiMH-only 01025 on LiPo.

[Dantona CMP-SC-28-37 on DigiKey](https://www.digikey.com/en/products/detail/dantona-industries/CMP-SC-28-37/19186145)
is a 12V/2.8Ah candidate, listed 115x46x43mm. Its permitted continuous/peak
discharge and compatible charger are not documented in the evidence reviewed.
It is not a qualified replacement. [FDK HR-SCU](https://www.fdk.com/product_e/nimh_e/tech_info/HR-SCU.pdf)
has high-current cell discharge curves and a
[DigiKey listing](https://www.digikey.com/en/products/detail/fdk-america-inc/HR-SCU/1202992),
but a loose cell is not a completed ten-cell pack, and a curve is not a
guaranteed pack rating. We have not selected a cell-assembly project.

The October 24 cardboard check established a 115x50x50mm envelope between
the chassis plates, with approximately 51.75mm usable height. The Tenergy
reference leaves 4.99mm gross height allowance; the Dantona listing would
leave 8.75mm with 43mm vertical. These are calculated allowances, before
straps, leads and local obstacles. Actual retention and installed fit are untested.

Before purchase, qualify the exact pack from course stock, DigiKey/Mouser or the
battery-only Amazon exception, and identify a compatible permitted charger
or request a specific exception for it. Normal current, peak duration, sag and protection
must be assessed together. No published Ah value alone establishes allowable
current; a high-current pack does not increase the L298's limits.

## Open package and mechanical checks

The [Boyd 6396BG drawing](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Cooling-High-Power-Extruded-6390.pdf)
specifies 41.91 × 25.4 × 25.4 mm. The old 28 × 16 mm reservation was too small.
We updated the drawing envelope, but it is not a validated installation.
The October 24 team reply relays Anson's acceptance of 6396BG for today's
review; he will investigate the mounting hardware. The part choice is settled
for this review, while the attachment remains a staff follow-up before assembly.
Boyd lists TO-218/TO-220 compatibility; L298N is Multiwatt-15. Verify the hole,
tab contact, mounting hardware and orientation on the actual course parts.
Final clearance and thermal performance depend on that installation. Electrical
DRC does not check an unattached heatsink.

The exact GCT drawing has been located, but contact pairing and recommended
pads have not been visually verified. Five switch footprints remain unassigned;
we have not substituted an arbitrary 4.5 mm switch.

The October 24 servo photos and team report establish the visible wire order
and reported functions: black=GND, red=existing 5V supply, white=PWM. See
[Actuator-design.md](Actuator-design.md#october-24-servo-cable-identification)
for the planned J90 adapter mapping. Servo photo collection is complete;
exact pitch/keying, wire gauge and finished-adapter continuity are unverified.

The October 24 motor/encoder photo and accompanying report also establish
the pictured harness's top-to-bottom order: red=motor lead 1, orange=encoder
supply, yellow=A, blue=B, gray=encoder ground, black=motor lead 2. These are
the attached jumper colors, not colors assigned to the motor's black ribbon
cable. The adapter mapping is recorded in Actuator-design.md.

The October 24 actual-Pi caliper reply supports the nominal 35 mm chassis /
22 mm Pi stack; see Mechanical-evidence.md. No repeat height measurement is
requested. Review remaining cable/port/steering envelopes and heatsink
installation where they affect fabrication. Second-harness agreement, adapter
mating/continuity, wire identification and encoder signal checks belong to
harness preparation/bring-up unless a connector change would alter PCB pads.
Battery retention and lead routing follow the final pack choice. The battery envelope has passed the team's cardboard check.
The four chassis center positions and 4.5 mm diameters are already established.
The team also confirmed the chassis holes are smooth through-holes. Their
diameter does not set the spacer thread: the proposed M3 fasteners use washers
to bridge the larger chassis holes. Actual thread engagement remains a fit check.

## External hardware selected for review

The purchasing BOM now itemizes these parts instead of assigning anonymous
hardware selection to the team. Quantities below include spares and mean
individual pieces, except where wire length is stated. Supplier pack sizes,
stock, cost and lead time must be checked before an order; none is reserved.
DigiKey-listed substitutes below replace the earlier direct-vendor hardware.
Stock was visible on October 24 but is not reserved. Prices may change.

| Use | Selected part/specification | Installed + spare | Reason and remaining fit check |
|---|---|---|---|
| Isolation/termination/recovery caps | [Samtec SNT-100-BK-T-H](https://www.samtec.com/products/snt-100-bk-t-h) | 18 + 2 | 2.54mm pitch, handle for removal. Twelve isolation + four termination caps installed normally; two BOOT0 recovery caps stored off-board. Check adjacent-cap access. |
| Chassis spacers | [Wurth 970350365](https://www.we-online.com/components/products/datasheet/970350365.pdf) | 4 + 1 | M3 female/female, 35mm body, nylon, 6mm across flats. Preserves proposed board height; smooth chassis holes confirmed; check access underneath. |
| Chassis screws | [Wurth 97790803111](https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/97790803111/10056388) | 8 + 2 | M3x8 nylon, one screw into each end of each spacer. Confirm plate thickness and thread engagement. |
| Chassis washers | [Essentra MFW030A](https://www.digikey.com/en/products/detail/essentra-components/MFW030A/4105389) | 8 + 2 | Nylon, 3.2mm ID, 7mm OD, 0.5mm thick. Under screw heads; lower washer bridges the measured 4.5mm chassis hole. |
| Pi spacers | [RAF M1269-2545-AL](https://www.digikey.com/en/products/detail/raf-electronic-hardware/M1269-2545-AL/7680971) | 4 + 1 | M2.5 female/female, 22mm body, 4.5mm hex across flats, about 5.20mm across corners. Reserve a 5.5mm hardware envelope; actual socket engagement remains untested. |
| Pi screws | [Essentra 50M025045P005](https://www.digikey.com/en/products/detail/essentra-components/50M025045P005/11639454) | 8 + 2 | M2.5x5 nylon, 5mm pan head. No spacing washers; verify adjacent components and thread depth. |
| Encoder housings | [Harwin M20-1060400](https://www.harwin.com/products/M20-1060400) | 2 + 1 | Four-position 2.54mm female housing for 0.64mm square pins; not keyed, so mark pin 1. |
| Encoder contacts | [Harwin M20-1180046](https://cdn.harwin.com/pdfs/IS-15.pdf) | 8 + 4 | Loose tin contacts, 22-30AWG. Requires matching crimp tooling and wire dimensions. |
| Servo adapter donor | [SparkFun 19224 / ROB-19224](https://www.digikey.com/en/products/detail/sparkfun-electronics/19224/16511100), candidate only | 1 adapter need; no released purchase | DigiKey 1568-19224-ND supplies the required male servo end with documented 26AWG wire. Contact-current rating and actual fit remain unverified. See the review below; do not directly crimp its 26AWG into the selected 20-22AWG Hirose terminal. |
| Charger housing | [Hirose DF63A-2EP-3.96C](https://www.hirose.com/en/product/p/CL0680-0535-5-00) | 0 requested; reference only | Charger selection and its actual lead are unresolved. |
| Charger contacts | [Hirose DF63-2022PC](https://www.hirose.com/en/product/p/CL0680-0539-6-00) | 0 requested; reference only | Contact choice depends on the selected charger lead; not the vehicle supply cable. |

The chassis stack is screw head / washer / PCB / 35mm spacer / chassis /
washer / lower screw head. Washers do not add to the 35mm board-to-chassis gap.
With a 1.6mm PCB and 0.5mm washer, an 8mm top screw engages about 5.9mm of
the spacer's 10mm thread depth. Actual lower engagement depends on plate
thickness. This assumes a clearance hole, not a screw forced into unmatched
chassis threads. The Pi stack uses 22mm spacers and approximately 3.4mm screw
engagement through a 1.6mm board; the selected connector and actual board
thicknesses still need a dry fit. Equal spacer heights matter for the 40-pin socket.

## Harness definition

We retain the board pin definitions in [Actuator-design.md](Actuator-design.md).
The [identified motor specification](../doc/HARDWARE.md)
already gives PH2.0-6PIN and encoder supply 3.3-5V. The October 24 team photo
and report now identify the pictured cable's order; manufacturer cavity
numbers and completed-adapter continuity have not been verified. The October 24 correction connects J82.1/J83.1 to the existing nominal
3.3V logic rail, matching the supply used in the earlier lab setup. Actual
voltage tolerance and signal quality still require hardware validation.

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
- **Charger reference only:** if the Tenergy pair is later accepted, preserve its Tamiya mating end and replace
  its clip end with DF63A-2EP-3.96C, using DF63-2022PC contacts on 22AWG wire.
  If the supplied lead is another size, use a correctly made transition,
  rather than an incompatible crimp. Verify positive-to-positive continuity
  with charger and pack disconnected. Charge the disconnected pack, not the PCB.
- **Servo:** board-side housing DF63-3S-3.96C and 20-22AWG contacts
  DF63A-2022SC are specified: J90 1=GND, 2=sensed6.6V, 3=PWM. A rated
  transition to the actual servo plug remains a purchasing exception.
  [DFRobot FIT0033](https://www.dfrobot.com.cn/goods-380.html) is listed at
  800mA, so we rejected it for the 3A servo endpoint despite its plug shape.
  SparkFun19224 is now a permitted-source candidate, not a qualified purchase.
  Adafruit973 lacks a verified wire/current rating in the reviewed listing.
  The Pololu2184 reference is on hold under the vendor rule. Neither a plug
  photograph nor wire gauge establishes a complete harness current rating.
- **Wire:** request cut lengths of [Alpha3057](https://www.alphawire.com/products/wire/hook-up-wire/premium/3057)
  stranded16AWG (3m red +3m black, including spare/routing allowance) and
  [Alpha3051](https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=3051)
  stranded22AWG (1m red +1m black for charging). Equivalent documented lab
  wire avoids buying whole reels. Wire gauge is not a universal ampacity:
  final routing, insulation, bundling, length and temperature enter the check.

Contact models and wire ranges are selected; verify access to compatible
crimp tools or purchased precrimp leads before buying loose terminals. We
have not assumed a generic crimper produces a qualified Hirose connection.

### Servo lead sourcing result — October 24

We identified [SparkFun 19224](https://www.digikey.com/en/products/detail/sparkfun-electronics/19224/16511100)
(manufacturer SKU ROB-19224; DigiKey 1568-19224-ND) as a candidate for TA
review. The listing showed 19 available at $2.25 each on October 24; stock
is not reserved. [SparkFun](https://www.sparkfun.com/servo-to-pigtail-cable-shrouded.html)
specifies 170mm, 26AWG and a shrouded male servo connector. Its
[drawing](https://cdn.sparkfun.com/assets/8/4/e/3/6/Schematic-19224-Servo_to_Pigtail_Cable_-_Shrouded.pdf)
identifies a 2.54mm JR-FU housing, but gives no continuous or timed peak
current rating. We therefore have not qualified it for the servo's published
2.4-3A stall range. The 4A regulator allocation is headroom, not a measured
servo demand or a harness rating.

| Alternative checked | Result |
|---|---|
| DFRobot FIT0033 | Published 800mA rating; rejected for this servo endpoint. |
| [Adafruit973 on DigiKey](https://www.digikey.com/en/products/detail/adafruit-industries-llc/973/5353631) | Appropriate connector description, but reviewed manufacturer information does not establish wire size or current rating. |
| Pololu2184 | Documented 22AWG; permitted supplier and complete contact-current rating not verified. Zero purchase quantity. |
| [TE AMPMODU MTE](https://www.te.com/content/dam/te-com/documents/industrial-automation-and-control/global/ENG_DS_4-1773458-0_AMPMODU_MTE_INTERCONNECT_SYS_0411.pdf) | Published 3A limit is for one contact in free air; housing compatibility with our servo is unverified. Not a qualified substitute. |

The BOM preserves one unresolved adapter requirement, with the SparkFun
candidate and supplier link attached. It does not add a second donor purchase.
Our review question is: **Which course-stock or recommended lead should we
use for the LD-1501MG? SparkFun19224 is available from DigiKey, but its
published information does not establish the required current capability.**

If that candidate is accepted for further qualification, its 26AWG tails need
insulated transitions to 22AWG leads for the existing Hirose contacts. The
transition does not increase the rating of the thinner cable or servo plug.
The conditional wiring plan is in [Actuator-design.md](Actuator-design.md).
The original servo lead stays intact. Fit, continuity, retention, voltage
drop and heating must be checked before vehicle operation; no such test is
claimed for the October 24 review.

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

**Three purchasing exceptions need resolution or explicit review: battery,
charger and servo-side adapter lead.** The separate heatsink-attachment row
stays in the BOM as a deferred staff follow-up, not a kit to order or a task
that must be solved tonight. The team reports that Anson accepted 6396BG for
the October 24 review and will investigate its mounting hardware. Boyd's
published package list is TO-218/TO-220; our L298N is Multiwatt15. We have not
verified a generic TO-220 mounting kit. After staff identifies the attachment,
confirm the screw length, nut, thermal interface and installed clearances.

No purchases or fabrication release have been made. The active board BOM
remains [BOM-Hand-assembly.csv](BOM-Hand-assembly.csv); off-board substitutions do not alter the circuit. The separate encoder-supply
correction changes only J82.1 and J83.1 from /+5V to /+3V3.

## October 24 mechanical substitution check

The RAF spacer has a 4.5mm hex across flats, approximately 5.20mm across
corners; it is not a 4.5mm round spacer. A 5.5mm envelope fits within the
existing 3mm-radius Pi reservation. The nearest nominal socket-body edge is
3.345mm from the hole center, leaving 0.595mm to that envelope. This is a
2D clearance calculation, not an assembled-Pi check. The course's possible
3mm-from-hole-edge interpretation remains open.

The RAF drawing specifies at least 4.70mm threaded depth. A 5mm screw through
an assumed 1.6mm board engages about 3.4mm, avoiding the tighter bottoming
margin of the former 6mm screw. Confirm actual board thickness and engagement
on assembly. Nylon screws avoid a large conductive head but still require
sensible tightening and a vibration/retention check. No mechanical load test
has been performed.

## Resistor sourcing alternatives (October 24)

The original R420 RT0603BRD0775KL and R432 RC0603FR-0722KL listings are
out of stock. Their design identities remain in the schematic; the active BOM
explicitly permits the following procurement alternatives, two of each
(one installed plus one spare), instead of buying both versions:

- R420: [Susumu RG1608P-753-B-T5](https://www.digikey.com/en/products/detail/susumu/RG1608P-753-B-T5/1240628),
  75kΩ, 0.1%, 0.1W, 0603, 25ppm/°C.
  [Manufacturer RG specification](https://www.susumu.co.jp/dl/?filename=n_catalog_partition01_en.pdf&type=application/pdf).
- R432: [Panasonic ERJ-3EKF2202V](https://www.digikey.com/en/products/detail/panasonic-industry/ERJ-3EKF2202V/1746336),
  22kΩ, 1%, 0.1W, 0603, ±100ppm/°C.
  [Manufacturer ERJ specification](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf).

Both preserve the nominal resistor values, specified tolerances and 0603
footprints, so the nominal feedback calculations do not change. Listings
showed stock on October 24; stock is not reserved. Record the actual installed
MPN at assembly and use the required board land pattern.
