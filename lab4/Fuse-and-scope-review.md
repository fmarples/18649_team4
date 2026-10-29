# Required scope and input fuse review — October 29

## Current prototype review — October 29, later update

The selected course scope is ready for final team/TA prototype fabrication
review. We recommend retaining the present CAD for that review. The new
[operating review](Prototype-operating-review.md) uses 1.5 A for the bare Pi
and 0.3 A for other 5 V loads; sustained 3 A Pi operation is a deferred stress
case. This is a planning assumption, not a measured or enforced limit.

At 1.5 A the calculated Pi voltage is 4.916–4.934 V before transients under
the stated hot-copper/contact/return assumptions. Planning battery current is
2.19–2.50 A. The normal-load loss review is complete; startup, actual workload,
fuse/harness selection and temperature checks remain required during assembly
and controlled bring-up before LiPo operation. The 10 A fuse does not qualify
continuous high-current PCB operation or protect every semiconductor.

The following earlier calculations retain their original stress assumptions.
They are not the current list of unfinished fabrication tasks. See
[Fabrication-review.md](Fabrication-review.md) for release stage and deadline.

We keep the course L298 circuit and omit the optional hardware current limiter
and camera. [Tom confirmed that the extra limiter is optional](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793289494772009),
and the team selected the required scope only. No further TA decision is
needed on that choice. This does not turn the existing filtered current ADCs
into fast protection or establish a safe motor-stall duration.

## Input fuse

We retain 0297010.L, 10 A, as the input-fuse candidate: one in the pack-side
0FHM0001ZXJ holder and one in the PCB's Keystone 3568 holder. Both are in the
positive path. The upstream fuse covers the cable before the board; two equal
fuses do not guarantee which opens first. The 14 AWG holder tails require
an insulated transition to the selected 16 AWG Hirose contacts.

The [current Littelfuse datasheet, revision 09/27/2024](https://www.littelfuse.com/assetdocs/littelfuse-datasheet-297-mini32v?assetguid=42c9dd21-a88e-4328-8e67-2f832444faf1)
specifies 32 V DC and a 1,000 A interrupt rating. For the 10 A part, 11 A can
persist for at least 100 hours; 13.5 A opens in 0.75–600 s; 20 A in 0.15–5 s.
Its typical cold resistance is 7.42 mΩ and typical melting I²t is 122 A²s.
The I²t figure is not a guaranteed total-clearing energy or a low-overload
trip model. It differs from older catalog revisions.

Using that cold resistance for both fuse elements gives:

| Previously calculated input case | Two-fuse drop | Two-fuse dissipation |
| --- | ---: | ---: |
| 3.41 A planning case | 50.6 mV | 0.173 W |
| 6.91 A heavy-load sensitivity | 102.5 mV | 0.709 W |
| 7.78 A full-allocation sensitivity | 115.5 mV | 0.898 W |

These are additional illustrative losses, not a rerun of the complete input
network: hot resistance, holder contacts and harness losses are omitted.
The [older manufacturer's derating table](https://www.mouser.com/datasheet/2/240/Littelfuse_MINI_Datasheet-1077557.pdf)
gives typical allowable loads of 8.6/8.0/7.3 A at 40/60/80 °C for this series.
It explicitly depends on the installation; use it as a sensitivity, not a
guarantee. The 7.78 A case therefore lacks high-temperature continuous margin.

The [14 A DF63 two-position rating](https://www.hirose.com/en/product/series/DF63/documents?path=/api/v1/series/DF63/documents/product_series_catalog/content?lang%3DEN)
and fuse's 10 A marking alone do not prove protection of the main input path.
Review the main input copper/vias, harness transitions, contacts and temperature
against the fuse's opening behavior. A main fuse is not intended to qualify
every signal branch or protect an L298 bridge at its 2 A DC absolute maximum.
The 10 A candidate remains conditional for that input-path review; optional
per-motor hardware protection is not a missing course requirement.

## What is complete, and what remains

Complete: the course-scope decision, published fuse opening-time comparison,
two-fuse loss calculation and temperature sensitivity. No chassis measurements
or additional hardware-limiter design are needed to complete these records.

Still required before fabrication release: review the main power path and
prototype operating envelope, including Pi voltage/transient margin and
converter heat. This is not a claim that the course requires the main fuse
to protect every component or thin signal branch during any possible fault.
Its required purpose is input/harness protection; the optional per-motor
limiter remains excluded. Assembly-process and servo-harness decisions can
be settled before assembly. The donor remains conditional because its rating
is undocumented. Actual stock/order quantities come from the team or supplier.

Before powered operation, integrate and test the existing battery guard and
motor-enable gating; verify harness polarity/continuity and perform controlled
startup/load/temperature checks. Those are unperformed implementation and
prototype checks, not new measurements required for the paper design.
