# L298N and 6396BG mounting

27 October 2026. We can define the mounting from the manufacturer drawings.
We do not need another lab measurement to identify the attachment method.
The active PCB still needs the anchor holes, nearby placement changes and
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

## Placement findings and remaining CAD work

[check_heatsink_mount.py](check_heatsink_mount.py) reads the saved board and
produces [the coordinate/clearance report](Heatsink-mounting-check.json) and
[the top-view study](Heatsink-mounting-study.svg). It makes no PCB changes.
The library footprint `Lab4_Mechanical:Boyd_6396BG_StraightPins` is prepared
and loads in KiCad with two checked pads and one closed courtyard. It reserves
conservative fin/web space while leaving the central device channel open.
It is not yet installed in the active board, and the screw/tool-access
reservation must be applied with the paired L298 placement.
Coordinates below are KiCad absolute millimeters; subtract (40, 40) for the
board-relative origin.

At the current U80 position, the back face of its tab is y = 57.76 mm. Placing
the 1.57 mm web behind that face gives anchors at **(59.30, 56.975)** and
**(84.70, 56.975)**. The sink's outer rectangle starts at (51.045, 44.275).
The KiCad even-row-to-tab datum is 4.50 mm, within ST's 4.25–4.85 mm interval.

The former 15-courtyard result used a tentative full rectangle at a different
y position. It is preserved as historical evidence in
[Heatsink-envelope-check.json](Heatsink-envelope-check.json), not used as the
current count. The new conservative fin/web blocks plus 0.5 mm clearance
intersect **C800, C801, C802, D800, D801, D802, H1, J80 and J81**. This is a
screen against courtyards, not a measured physical collision. U80 occupies
the intended central channel and is excluded from that count.

A nearby placement search keeps all chassis supports fixed. Moving U80 and
the sink **+3 mm in x and −3 mm in y** leaves only **C800, C802 and J80** in
the conservative clearance screen. This is the preferred candidate for the
next placement pass, not an implemented or fully qualified placement. The
search does not assume that existing copper moves safely with components.

Remaining design work is digital:

1. Install a two-anchor heatsink footprint using the published hole geometry.
   Reserve the fins, web, screw and tool-access spaces. Any intended overlap
   with U80 must be specifically documented rather than disabling general
   courtyard checking.
2. Move U80 and the affected neighbors, retaining the local bypass and motor
   current paths. Reconnect its 15 pads and all displaced traces. The two
   anchors at the existing location already intersect copper on three nets;
   these are not spare mounting locations in the routed board.
3. Refill all planes and check all-layer pad/hole/copper clearance, electrical
   DRC, schematic parity, connectivity, labels and local power/return paths.
4. Re-evaluate the finalized cooling arrangement and operating duty. A valid
   mounting geometry does not establish a safe stall duration or continuous
   L298 current. See [Power-margin-review.md](Power-margin-review.md).

No new physical measurement is requested for these steps. If the delivered
sink is a different variant, or the course supplies a different attachment,
record that change and compare it with this plan before assembly.
