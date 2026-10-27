# L298N and 6396BG mounting

27 October 2026. We can define the mounting from the manufacturer drawings.
We do not need another lab measurement to identify the attachment method.
The active PCB includes the anchor holes, nearby placement changes and
affected copper rerouting. This review does not qualify operating temperature.

## Mounting we will use

The **6396BG straight-pin variant** has two solderable PCB anchors. One M3
steel screw and nut clamp the L298N's metal tab against the sink's central
web. We will use a thin thermal-grease layer at that interface. The PCB anchors
support the sink; the screw provides the pressure needed for heat transfer.

The L298 tab is connected to pin 8, ground. Our proposed installation accepts
that ground potential, so a separate electrical-insulating pad is unnecessary.
Neither anodizing nor grease provides dependable electrical isolation or a
dependable ground bond. The anchor pads must not carry operating current.
Keep unrelated copper and components clear of the metal body and fasteners.

[Boyd's catalog, printed page 60 (PDF page 62)](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Heatsinks-Catalog.pdf)
specifies these dimensions:

| Feature | 6396BG dimension / design choice |
| --- | --- |
| Body, width × depth × height | 41.91 × 25.40 × 25.40 mm |
| Anchor center spacing | 25.40 mm |
| Straight anchor projection below body | 3.96 mm |
| Recommended finished plated PCB holes | 2.89 mm diameter |
| Proposed pad diameter | 4.50 mm; 0.805 mm nominal annular ring |
| Device screw hole | 3.81 mm diameter, unthreaded |
| Screw center above sink base | 19.05 mm |
| Central web thickness | 1.57 mm |

Do not substitute the **6396B-P2G** drawing: its shoulder pins use different
PCB holes. The current [6390-family sheet](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Cooling-High-Power-Extruded-6390.pdf)
is a complementary body/variant reference; its pin-detail dimension is not
the recommended PCB drill. Specify the finished plated hole to the fabricator.

## Vertical fit calculation

We used [ST's L298 Multiwatt15 vertical drawing and dimension table,
pages 12–13](https://www.st.com/resource/en/datasheet/l298.pdf), with the sink
base at the top of a nominal 1.6 mm PCB. ST specifies a 3.65–3.85 mm tab hole,
which accepts the chosen M3 screw. Its 20.2 mm maximum body width fits the
nominal open channel between the two anchor/fin regions.

| Check | Arithmetic | Calculated clearance |
| --- | --- | ---: |
| Lead below PCB, dimension L | (21.9 to 22.5) − 19.05 − 1.6 | 1.25–1.85 mm |
| Minimum for the other lead row, L1 | 21.7 − 19.05 − 1.6 | 1.05 mm |
| Lead bend above PCB, L2 | 19.05 − (18.10 to 17.65) | 0.95–1.40 mm |
| Plastic body bottom above PCB, L3 and L7 | 19.05 − [(17.75 − 2.65) to (17.25 − 2.90)] | 3.95–4.70 mm |

These dimensions support a normal, uninsulated flush installation without
inventing a new lead shape. They are not a complete tolerance stack: Boyd's
full production tolerances and the final board thickness tolerance are not
included. Final dry fitting is an assembly check, not a prerequisite for
drawing the footprint.

## Hardware specification

We need **one assembly**, with no extra kit counted separately. Each kit
contains one of each item below plus enough compound for one thin interface.
Reuse equivalent course stock where available; its allocation is unconfirmed.
The linked purchases are from DigiKey/Mouser, as required for non-battery parts.

| Item | Specification and supplier reference |
| --- | --- |
| Screw | M3 × 0.5 × 12 mm steel pan-head, [Keystone 29314](https://www.digikey.com/en/products/detail/keystone-electronics/29314/1532209) |
| Nut | M3 × 0.5 steel hex, [Keystone 4708](https://www.digikey.com/en/products/detail/keystone-electronics/4708/4499301) |
| Flat washer, under screw head | M3 steel, approximately 3.2 mm ID × 7.01 mm OD × 0.53 mm, [MFWZ 003](https://www.digikey.com/en/products/detail/bfirst-industrial/MFWZ-003/274978) |
| Lock washer, under nut | M3 steel split washer, approximately 3.1 mm ID × 6.2 mm OD × 0.81 mm, [MLWZ 003](https://www.digikey.com/en/products/detail/bfirst-industrial/MLWZ-003/274983) |
| Thermal compound | Thin silicone thermal grease, [MG Chemicals 860](https://mgchemicals.com/downloads/tds/tds-860.pdf), e.g. 860-60G via [Mouser's 860 listing](https://www.mouser.com/en/c/?series=860), or documented course equivalent |

The washers' distributor minimum order quantities are larger than our one-kit
demand. Do not confuse a pack quantity or a shared compound container with the
number installed. No hardware or compound purchase has been placed.

With the maximum 1.6 mm tab, nominal 1.57 mm web, 0.53 mm flat washer, 0.81 mm
lock washer and 2.39 mm nut, the nominal clamp stack is 6.90 mm. A 12 mm screw
provides full nut engagement with about 5.1 mm protruding beyond the nut.
Allow roughly 8.3 mm behind the web for the nut/washer/screw tail, within the
nominal rear fin depth. Preserve tool access through the central channel.
This is a dimensional selection; check the delivered parts before tightening.

[ST AN260, sections 1.2 and 2.2](https://www.st.com/resource/en/application_note/an260-handling-and-mounting-ics-in-plastic-power-packages-stmicroelectronics.pdf)
provides the mounting sequence and Multiwatt screw guidance. Assemble the
device and PCB-mounted heatsink **before soldering** so tightening does not
strain already-soldered device leads. Use thermal grease and controlled
tightening; ST gives 0.8 N·m as the suggested maximum for the M3 arrangement,
not a torque we have validated on this assembly. Avoid over-tightening or
forcing the device leads to align. Solder the intended anchor pins, not the
anodized aluminum body. The heat sink's thermal mass may require a suitable
iron tip/preheat process; inspect the finished joints.

## Implemented placement and checks

The documented move is now implemented. U80 is at (66.11, 64.34) mm;
HS80 is at (75.00, 53.975) mm. C800 is at (88, 71.5), C802 at
(101.35, 47), and J80 at (67.1, 46.95). Chassis and Pi hole centers did
not move. These coordinates are absolute KiCad millimeters; subtract
(40, 40) for board-relative positions.

The installed anchor pads are (62.30, 53.975) and (87.70, 53.975).
The fin/web envelopes plus 0.5 mm contain no unrelated component courtyard.
The independent top-metal check finds no unrelated top copper within its
0.2 mm margin. Native DRC checks the plated anchors on every copper layer.
U80/HS80 alone have a deliberate courtyard-overlap exception for the clamp.

All displaced connections were rerouted and ground zones refilled. The
previous 15-conflict rectangle and placement candidates are historical
studies, superseded by [Heatsink-mounting-check.json](Heatsink-mounting-check.json)
and [the updated drawing](Heatsink-mounting-study.svg).

The remaining decision is operating current/duty and fault protection, not
the attachment method. Check actual dry fit, clamp retention and soldering
when assembling; temperature and stall behavior remain untested.
