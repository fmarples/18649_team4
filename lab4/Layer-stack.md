# Four-layer routing reference

26 October 2026. We use **JLC04161H-7628**, nominal 1.6 mm, as the
reference stack for the remaining layout review. The intended copper weights
are 1 oz outer / 0.5 oz inner. This records a design baseline, not an order or
a controlled-impedance qualification. Confirm the same stack in the final
fabrication package and order settings.

| Layer / material | Published thickness | Our use |
| --- | ---: | --- |
| F.Cu | 0.035 mm | Components, local signals, power and ground fill |
| 7628 prepreg | 0.21040 mm | Dielectric, published Dk 4.4 |
| In1.Cu | 0.0152 mm | Ground plane |
| Core | 1.065 mm | Dielectric, published Dk 4.6 |
| In2.Cu | 0.0152 mm | Signals and provisional supply branches |
| 7628 prepreg | 0.21040 mm | Dielectric, published Dk 4.4 |
| B.Cu | 0.035 mm | Pi socket, signals, power and ground fill |

Source: [JLCPCB stackup table](https://jlcpcb.com/impedance), checked October 26.
These are the fabricator's listed nominal values; they are not measurements of
our board. KiCad currently records four copper layers and nominal 1.6 mm board
thickness; the detailed physical stack is documented here.

In2 is much closer to B.Cu than to In1.Cu in this arrangement. We therefore
must review the bottom ground fill beneath inner signal routes as well as the
In1 plane. Merely moving a signal to an inner layer does not give it a
continuous nearby ground reference. CAN pair spacing, detours, layer changes
and return continuity still need final refinement. The initial
[CAN geometry audit](CAN-geometry-review.md) records the measured copper and
specific reference gaps; its nominal front-pair estimate is not a fabrication
impedance qualification.

The inner copper is thinner than the outer copper. The new supply joins
establish connectivity; they are not a final current rating. Before release,
check the worst supply-path voltage drop and widen or parallel the trunks as
needed. The multiamp Pi, servo and motor paths need their own copper-width and
via review. No hardware tests or fabrication approval are implied.
