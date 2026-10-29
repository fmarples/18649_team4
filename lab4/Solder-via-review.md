# Solder-pad via and aperture review

27 October 2026. The saved board has **zero nominal via-drill intersections
with SMD lands and zero sites inside the 0.15 mm drill-to-opening screen**.
[The checker](check_solder_vias.py) records actual pad shapes and the board
hash in [Solder-via-check.json](Solder-via-check.json).

## Completed changes

The earlier 6164a13 baseline had 98 intersections. Previous revisions moved
97 vias and removed one redundant ground via. This revision moves another
32 existing vias to provide more drill clearance: the original 13 sites
inside 0.10 mm and 19 additional sites found by the tighter 0.15 mm screen.
Neighboring traces were rerouted where needed. C244.2 also required two short
3.3 V segments to use 0.8/0.6 mm widths; their loss is included in the updated
supply calculation. Footprint positions, pad shapes/nets and the CAN backbone
are unchanged. See [Routing-change-check.json](Routing-change-check.json).

C7.2 keeps thermal relief. Rotating its spoke pattern from 90 to 45 degrees
restored its connection after nearby copper changed; we did not make this
pad solid to avoid the thermal-spoke finding.

## Fabrication tolerance and apertures

[JLCPCB capabilities](https://jlcpcb.com/capabilities/Capabilities) list hole
position tolerance ±0.075 mm and through-hole diameter +0.13/−0.08 mm.
The positive radius allowance is 0.065 mm, so their sum is 0.140 mm. Our
0.15 mm nominal screen covers those two allowances only. It is **not** a
mask-registration guarantee, a qualified mask dam or proof of sealed tenting.
The fabricator supports 1:1 mask openings; its published mask-bridge limits
depend on mask color and copper weight. Recheck the chosen manufacturing
settings and final artwork before release.

All 973 vias request front/back tenting. All 798 SMD copper-pad sides have
zero effective mask expansion and paste margin. Q1.2 intentionally lacks a
direct paste layer: four separate 3.05 × 2.75 mm windows provide its paste.
Their presence is verified; deposited paste volume depends on stencil
thickness and the selected process. Tenting does not mean filling/capping.

The checker reports raw overlaps separately from near-opening gaps and
accepts an explicit `--review-gap-mm`. Nominal geometry and automated DRC
cannot establish drill registration, solder quality or stencil performance.
Final manufacturing exports must be inspected after the remaining design
changes; this review is not a fabrication release.

## October 28 capacitor-bank revision

The larger 1210 output pads initially covered twelve existing ground-via
holes. We moved those vias and repaired their ground branches, keeping both
vias per original output ground pad. The refreshed check finds zero drill/land
intersections and applies the same 0.15 mm nominal drill-separation sensitivity.
No via filling/capping or reliable tent sealing is assumed. Final mask/paste
export inspection remains part of manufacturing review.
