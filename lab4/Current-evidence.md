# Current evidence and measurement record

24 October 2026. We distinguish component ratings, calculated allocations and
measurements. Average current on the new PCB is unmeasured; it has not been built.

## October 24 review clarification

The October 24 team message relays Anson's confirmation that measured motor
stall current and L298 loss/temperature are not necessary for today's review.
The team also recorded in the shared checklist that the listed measurements
can wait. We therefore submit the sourced calculations and labeled assumptions
without treating these measurements as a prerequisite for October 24.
They remain unmeasured; the clarification does not validate the estimates or
qualify the assembled circuit. Later hardware validation remains necessary.

The same reply accepts the proposed 6396BG heatsink for the review. Mounting
hardware is unresolved and Anson will investigate it. Acceptance of the part
does not establish its attachment, tested temperature or safe stall duration.
The [shared report](https://docs.google.com/document/d/1zMR_S5QoFPES1BhswG5bhpLGAib2P71ri6rK2hKzBcc)
records this review status. No battery vendor exception was supplied in this reply.

## Existing Lab 2 evidence

The September 28 record in [CURRENT_SENSOR_HANDOFF.md](../doc/CURRENT_SENSOR_HANDOFF.md)
contains nominal telemetry: left/right rest medians of +735.5/+700 mA and running
medians of +617/+588.5 mA. The servo median was about +686 mA while holding; that
is not a servo-motion test. Sensor orientation, zero and gain were unresolved,
and those motor readings preceded the polarity correction. These are recorded
telemetry values, not calibrated physical current values.

We cannot use their absolute values, subtract the rest medians, or combine them
to claim measured battery consumption. A powered servo holding position is not
a zero-current reference. No calibrated Pi/logic/CAN average-current record has
been identified.

## Values used for design

The 6.4 A motor entry is twice the handout's 3.2 A motor stall specification.
It is a stress case, not ordinary driving current or a permissible L298 operating
current. The 4 A servo, 3.3 A 5.1 V rail and 0.8 A logic entries are allocations.
At 12 V and assumed 85% converter efficiency, the combined battery stress case
is approximately 10.9 A. It is not a measured peak. Average current and runtime
remain unmeasured.

For measured rail averages at their actual voltages:

`Ibat ≈ Imotor_supply + (Vservo·Iservo/ηservo + V5·I5/η5 + Vlogic·Ilogic/ηlogic)/Vbat`.

Winding current in a PWM-driven motor is not generally equal to average battery
current. Direct battery-input measurement avoids that conversion ambiguity.
`Runtime ≈ usable capacity / average battery current` is only a first estimate;
discharge rate, voltage cutoff and temperature affect usable capacity.

## Estimates and assignment requirements

We can use datasheet-based calculations and explicit operating assumptions to
develop the schematic and preliminary power budget. A nominal sensor reading
with unresolved calibration is not a reliable estimate of physical current.
We do not need a separate measurement campaign for every design iteration.

The Lab 4 handout, Part 1.1 (page 3), requests a four-rail table containing peak
and average current, and explicitly asks for measured motor stall current,
L298 voltage drop and stall temperature behavior. Page 12 requires numbers to
identify their measured or datasheet basis, with a method for measurements.
Therefore an unsupported guess cannot be presented as a completed answer.
Any provisional estimate must name its source/assumption and pending check;
course staff have now confirmed the above measurement deferral for October 24.

Current-measurements.csv is an optional team recording aid. It is not an extra
deliverable and its full set of suggested conditions is not a new requirement.

## Measurement protocol

Use [Current-measurements.csv](Current-measurements.csv) for idle, representative
running, steering, startup and combined-load observations. Record voltage,
average current, interval, instrument, calibration and raw evidence. Leave peak
current blank if the instrument cannot capture the transient.

1. Use the working lab setup at its verified supply settings. Record firmware
   and wiring. This informs the design but does not test an unbuilt converter
   or a different servo supply voltage.
2. Verify each sensor's zero with no current through its sensing path, then
   compare a known nonzero load with a reference current measurement. Preserve
   current direction and record calibration coefficients and reference method.
3. Measure rest, representative motor operation, unloaded steering sweep,
   representative steering load and simultaneous operation. Record a consistent
   interval, such as 30 seconds, for averages. Record startup peaks separately.
   A stall test is not an average-load test.
4. Record loaded voltage at the device/rail. A supply display measures its whole
   connected load, not individual motors or servo. A slow display does not
   establish a fast peak.
5. Repeat on the assembled PCB at 6.6/5.1/3.318 V, including sag, overshoot and
   temperature. Earlier measurements do not establish these new rail behaviors.

The requested motor stall/loss/temperature evidence remains incomplete.
Arrange a course-supervised method compatible with the driver limits; the
handout's ten-second temperature question is not permission to exceed them.
The October 24 review uses the staff-confirmed deferral above. A calculation
or an uncalibrated log does not become a measurement because it was deferred.


## October 24 servo source review and preliminary average case

The [Hiwonder chassis specification](https://www.hiwonder.com/products/ackermann-steering-chassis)
names **LD-1501MG**, with **100mA no-load** and **2.4-3A stall** current. This is
an exact-model supplier source. The LD-3015MG product page is a different model
and is excluded from our LD-1501MG evidence. The exact-model listing does not
give the voltage/test method for these current values or define whether
no-load means static holding or unloaded motion. We use100mA as a provisional
no-load reference, not a measured static-hold value at6.6V. Source lookup is
complete; the condition-specific measurement remains open.

For the existing10mOhm shunt and INA180A2 gain50, Vout=0.5V/A. At100mA this
gives1mV shunt drop,50mV output and about62 ideal counts (12-bit,3.3V reference).
At3A it gives30mV drop,1.5V output and0.09W shunt dissipation. The proposed
20mA change gives10mV, about12.4 ideal counts. The1W shunt rating therefore
has arithmetic margin at the published stall endpoint, subject to its thermal
conditions; offset/noise and the actual ADC/reference still need validation.
Sources: [TI INA180](https://www.ti.com/lit/ds/symlink/ina180.pdf),
[Vishay WSL2512](https://www.vishay.com/docs/30100/wsl.pdf).

We prepared a **preliminary planning case**, not a measured or guaranteed
average. It assumes both motor supply loads at the catalog rated0.36A each;
servo current at100mA for90% of the interval and3A for10%; and continuous use
of the existing3.3A Pi/devices and0.8A logic allocations. The90/10 split is a
design assumption, not observed behavior. The3A point comes from the published
stall endpoint; this calculation does not recommend sustained stalls. Treating
motor winding current as supply current is also a planning simplification.

| Rail | Assumed average in this case | Basis |
|---|---:|---|
| Motor supply |0.72A|2 x0.36A catalog rated point; full-time supply-current proxy|
|6.6V servo|0.39A|0.90 x0.100 +0.10 x3.0|
|5.1V Pi/devices|3.3A|Existing allocation assumed continuously consumed|
|3.318V logic|0.8A|Existing allocation assumed continuously consumed|

Regulated output power=6.6 x0.39+5.1 x3.3+3.318 x0.8=22.0584W.
At nominal12V and assumed85% converter efficiency,
Ibat=0.72+22.0584/(12 x0.85)=**2.883A**. This provides a transparent case for
review; it is not a fuse rating, a validated maximum or a runtime guarantee.
The electronics allocations are intentionally pessimistic consumption
assumptions, but rated motor current and an assumed steering duty cycle do
not bound all driving. Keep the separate peak/stall stress cases.

Power-budget.csv now records these provisional estimates. Power-calculations.json
preserves the inputs and unrounded arithmetic. Confirm the operating profile
with the team/TA or replace it with measured averages. Motor stall and
L298-drop/temperature evidence remain unmeasured, with deferral confirmed for
the October 24 review.
