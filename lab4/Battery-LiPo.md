# 3S LiPo battery revision — October 28

We selected a CNHL S220403BK shorty pack and Hitec RDX1 Mini (44295) charger
for the design. [Anson approved this replacement pair on October 28](https://18449-f26.slack.com/archives/D0C53Q3DN9X/p1793220604820219). Amazon is allowed for both. The old
NiMH entries now have zero requested quantity. Nothing has been ordered.

| Item | Selection and evidence |
|---|---|
| Battery | [Amazon B0DQP7SKGV](https://www.amazon.com/dp/B0DQP7SKGV), a **two-pack** listing. Request one listing: one battery in the car, one spare. |
| Pack specification | Standard 3S LiPo, 11.1 V nominal, 12.6 V fully charged, 2.2 Ah, XT60 main lead and JST-XH balance lead. [CNHL specifies](https://chinahobbyline.com/products/cnhl-black-series-shorty-2200mah-3s-11-1v-40c-lipo-battery-with-xt60-plug) 40C continuous: 2.2 Ah × 40/h = 88 A advertised capability. This is a manufacturer rating, not our measurement or a permitted vehicle current. We do not use the duration-unspecified burst rating. |
| Charger | [Amazon B07ZDKT6BD](https://www.amazon.com/dp/B07ZDKT6BD), Hitec 44295/HRC44295. [Hitec specifies](https://hitecrcd.com/rdx1-mini-one-port-65w-ac-battery-charger/) 65 W AC operation, 2–4S LiPo support, balance/storage modes and an XT60 output. |
| Fit | CNHL lists 77 × 33 × 26 mm and possible 1–5 mm dimensional variation. Applying +5 mm to every dimension gives 82 × 38 × 31 mm, within the team's checked 115 × 50 × 50 mm envelope. This covers the pack body; secure the leads and retain the pack without compressing or puncturing it. |

Price, seller, exact listing variant and arrival date must be checked when
ordering. We have not reserved stock. The dimensional calculation does not
claim a finished mounting or connector-mating test.

## Power and wiring

The three buck converters already use an 8–15 V electrical design envelope.
The LiPo's voltage range therefore does not require new regulator setpoints.
The 8 V qualification point is **not** a battery discharge limit. We propose
stopping drive at 10.5 V under load, comfortably above the handout's 9 V pack
floor. A total-pack reading cannot prove every individual cell exceeds 3 V.

The existing planning scenario becomes
`0.72 A + 22.0584 W / (11.1 V × 0.85) = 3.058 A` at nominal voltage.
At 10.5 V and an assumed 80% efficiency it is 3.346 A. These are calculated
scenarios; the motor-current proxy, duty cycle and efficiencies are not
measurements or guaranteed bounds. The 24.42 Wh nominal pack energy does
not establish runtime. See `Power-calculations.json` for sensitivity cases.

We keep J40's Hirose DF63 interface and use a separate XT60-to-DF63 vehicle
adapter: J40 pin 1 positive, pin 2 ground. The BOM adds SparkFun PRT-10474
connector pairs from DigiKey and a Littelfuse 0FHM0001ZXJ MINI inline holder
near the battery connector, upstream of the long adapter cable. Its 14 AWG
leads need an insulated transition to the selected 16 AWG DF63 contacts.
The PCB fuse cannot protect a short in the cable before it. The separately
listed 10 A fuse is still a coordination candidate; neither fuse establishes
fast protection of the L298 or permission to stall the motors.

The LiPo change does **not** remove the three DF63-2S-3.96C vehicle housings:
one mates J40 for the battery adapter, and two mate J80/J81 for the motors.
The existing spare is additional to those three installed housings. We solder
the XT60 solder cups and insulated wire transitions; we **crimp** the selected
DF63A-1618SC contacts before inserting them into the Hirose housings. Do not
substitute solder-filled crimp barrels. The former NiMH charger adapter
housing, male crimp contacts and charger-only wire have zero purchase quantity.
The new charger uses its own XT60/balance interface, not the motor connectors.

For charging, disconnect the pack completely from the vehicle. Use standard
**LiPo / 3S balance mode, 2.2 A, 4.20 V per cell**, with both the main and
balance leads attached as shown in the [Hitec manual](https://media.zenobuilder.com/upload/gatcxyxclp/RDX1-Mini-Manual-Web-48795484.pdf).
The supplied T-type adapter is not assumed to fit. The XT60 pairs allow a
dedicated correctly polarized charge lead if direct connection is unsuitable;
verify contact sex, polarity and continuity before connecting a battery.
Connect a detachable charge lead to the charger before the battery, and
disconnect the battery first so an energized free plug is not exposed.
Keep the factory balance lead intact. Charge under supervision, off the car,
in the handout-required LiPo charging bag. Course bag availability is open in
the BOM; no purchase source for the bag is claimed.

## Voltage monitor and shutdown

We added R580 = 100 kΩ / 0.1%, R581 = 10 kΩ / 0.1% and C580 = 100 nF,
feeding the already reserved Front U50 PA3 / ADC1_IN3. The divider reads the
protected battery rail, after the input protection. It does not connect the
pack to the MCU's low-voltage backup-supply pin named VBAT.

`VADC = Vpack / 11`: 12.6 V becomes 1.145 V, and the 15 V design ceiling
becomes 1.364 V nominal. Opposite 0.1% resistor corners give a 1.366 V maximum
at 15 V. The source resistance is 9.09 kΩ; nominal RC time constant is 0.909 ms.
Use 12-bit conversion, a 480-cycle acquisition at no more than 21 MHz,
at least 10 ms settling, calibrated VDDA and no internal pull resistors.
Enable brownout reset and retain the reset input state until VDDA is valid.
PA3 is an FT pin; see [ST DS10086](https://www.st.com/resource/en/datasheet/stm32f401re.pdf),
pin table and ADC/electrical limits. Power sequencing and accuracy still need
validation on the assembled board; resistor arithmetic is not that test.

`firmware/battery_guard.c` implements an explicit-arm state, a 10.5 V stop,
an 11.1 V minimum to arm, invalid/over-range rejection, a 100 ms freshness
limit and a latched fault. Voltage rebound cannot restart the car. The
nominal ADC conversion uses the /11 divider and a supplied calibrated VDDA.
The C tests cover startup, threshold boundaries, stale/invalid data, recovery
rejection and timer wrap. **This module is not integrated into either MCU
application and has not stopped a physical motor.**

Firmware integration must sample PA3 at 100 Hz, send fresh battery status
from Front to Rear through the existing CAN application, and gate **every**
motor-enable write at Rear. Startup, missing/stale battery status and a
latched battery fault must leave both L298 enables low. Integration must
preserve the Lab 3 message assignments and include loss-of-status testing;
we have not invented a new CAN ID here. A stop leaves electronics powered,
so the team must disconnect the pack promptly. This software guard is not
a BMS, per-cell monitor, or hardware battery disconnect.

Before battery operation, complete the firmware integration, calibrate the
voltage reading and demonstrate cutoff using a current-limited bench supply
or simulated ADC inputs. Do not deliberately over-discharge the LiPo to test
the threshold. Existing Pi voltage-margin, capacitor and motor-fault reviews
still apply to this power source.
