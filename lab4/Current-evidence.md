# Current evidence and measurement record

23 October 2026. We distinguish component ratings, calculated allocations and
measurements. Average current on the new PCB is unmeasured; it has not been built.

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
only course staff can accept a deferred required measurement at review.

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
Where evidence is unavailable at review, state that explicitly. A calculation
or an uncalibrated log does not replace a required measurement.
