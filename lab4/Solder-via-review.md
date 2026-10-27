# Solder-pad via and aperture review

26 October 2026. The saved board has **zero nominal via-drill intersections
with SMD copper lands**. `check_solder_vias.py` and
[Solder-via-check.json](Solder-via-check.json) record the source hash and checks.
An open drill through a solder land can draw solder away from the joint;
electrical connectivity alone does not assess this assembly detail.

## Completed routing changes

The baseline at revision 6164a13 had 98 intersecting vias across 96 pads.
We relocated 97 existing vias and removed one redundant ground via. The
latest pass moved the final 19 sites and rerouted neighboring traces at
their original widths. It added 11 signal/ground vias, with no added supply
vias. No footprint, pad geometry/net, zone setting, project rule or CAN
backbone changed. All 306 targeted connections and native ERC/DRC/parity pass.

C200.2's previously removed via was redundant with the nearby ground via at
(105.5, 89.3) mm; its pad and formerly attached traces still connect through
explicit copper. [Routing-change-check.json](Routing-change-check.json)
records the latest relocation coordinates and affected nets.

## Mask and paste configuration checked

All 970 vias request front and back tenting. All 798 SMD copper-pad sides
have zero effective mask expansion and paste margin. Q1.2 intentionally has
no direct paste layer: the TO-252 footprint supplies four separate
3.05 x 2.75 mm paste windows. This records their presence, not a completed
stencil-volume review.

We screened nominal drill edges against the zero-margin pad shapes at a
0.10 mm review gap. Thirteen sites are outside the solder lands but within
that gap. They were not newly introduced by the latest 19 moves. The gap is
an inspection target, not a manufacturer tolerance or an automatic failure.
Before release, review these sites against the chosen drill/mask registration
limits and exported artwork; move a via where the required margin is missing.

| Pad | Via UUID |
| --- | --- |
| C505.2 | df6f7576-f27e-4608-89ca-74cf7117356f |
| C6.1 | d8492c3b-186a-4e64-af9e-ffe989df2145 |
| C608.2 | 2fbaced2-35f8-4a72-b7d2-220c93c366de |
| R512.1 | 2a271dee-0f4d-4537-b629-0d6a380bfd3d |
| R550.1 | 5a6b2354-59c9-4503-8f93-d0a51489c1f8 |
| R651.1 | 13d05f75-0c53-43c2-8d9a-795f3dd1b076 |
| SW61.1 | a962726a-d665-48fb-8861-479f81e4fa43 |
| Y10.4 | bfa89817-ec06-4639-b17a-3d4bef1c84f4 |
| Y14.4 | e144ecb2-539a-444d-b206-7e2731e664e3 |
| Y20.4 | e0582a39-e62e-4796-8cca-ac7a012cb0f8 |
| Y24.4 | b7151081-a9d2-47b9-a667-3292d92e8f0f |
| Y30.4 | 16cf531f-489a-43ef-8872-436a486518d0 |
| Y34.4 | 485f3581-06e0-4627-9298-760429994e9a |

## Limits

Zero nominal overlap does not establish reliable tenting, drill/registration
tolerance, stencil aperture coverage or solder quality. Tenting is not filling
and capping. Exported mask/paste artwork and the final assembly process still
need review. No fabrication release or physical test is claimed.

An analytic checker fixture uses a 1 mm square pad and 0.30 mm drills:
a 0.05 mm edge gap is flagged by the 0.10 mm screen; a 0.85 mm gap is not.
Neither is counted as a nominal overlap.
