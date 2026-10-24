# Parts and physical interface review

23 October 2026. We reconciled the design with the course's
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
  F1 identifies the Keystone 3568 holder. Its fuse element is separately listed
  and unselected: buying a holder does not provide overcurrent protection.
- Manufacturer/source fields are filled for placed named circuit parts.
  Exact stock must be checked when ordering. The 75 kΩ 0.1% and 22 kΩ resistor
  listings need an availability/substitute check; preserve feedback tolerances.

## Selected battery and charger

We selected Tenergy 11609 and charger 01025 as our design/BOM baseline.
Dantona CMP-AA-21-37 is retained only as a historical comparison, with zero
requested quantity; its maximum discharge current was not established. The selected pack,
[Tenergy 11609](https://power.tenergy.com/at-tenergy-12v-4200mah-nimh-rechargeable-battery-pack-10s1p-50-4wh-30a-rate/),
uses ten **Sub-C**, not AA, NiMH cells: 12 V / 4.2 Ah, manufacturer-stated 30 A
continuous discharge, 115 × 44.4 × 46.76 mm, approximately 1.3 lb. Listed
build-to-order lead time is 3–7 business days; verify at purchase.

Tenergy lists [01025](https://power.tenergy.com/tenergy-smart-universal-charger-for-nimh-nicd-battery-packs-6v-12v-ul/)
as compatible: NiMH/NiCd, 5–10 cells, selectable 1/2 A, negative-delta-V
termination. Supplied Tamiya/clip leads do not mate directly with our Hirose
connector. A keyed, correctly polarized adapter is needed. This recommendation
now accompanies the selected 11609 pack. Neither item has been ordered.
On October 23 the manufacturer lists $118.99 for the pack and $26.69 for the
charger, or $145.68 before tax/shipping and adapters. Purchasing and delivery
remain to be confirmed; the design selection is not an order.

Check the pack's full dimensions, retaining strap and cable exit against its
intended location. A larger-current pack does not raise the L298's limits.
Only 11609 and 01025 are requested in the purchasing list. Allow clearance
for the strap, leads and connector beyond the stated pack dimensions.

## Open package and mechanical checks

The [Boyd 6396BG drawing](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Cooling-High-Power-Extruded-6390.pdf)
specifies 41.91 × 25.4 × 25.4 mm. The old 28 × 16 mm reservation was too small.
We updated the drawing envelope, but it is not a validated installation.
Boyd lists TO-218/TO-220 compatibility; L298N is Multiwatt-15. Verify the hole,
tab contact, mounting hardware and orientation on the actual course parts.
Final clearance and thermal performance depend on that installation. Electrical
DRC does not check an unattached heatsink.

The exact GCT drawing has been located, but contact pairing and recommended
pads have not been visually verified. Five switch footprints remain unassigned;
we have not substituted an arbitrary 4.5 mm switch.

Physical checks still needed: original motor/encoder/servo plug shapes, pin
order and wire gauges; actual encoder supply/output type; heatsink fit;
selected battery fit; and the proposed Pi/chassis vertical spacer stack.
The four chassis center positions and 4.5 mm diameters are already established.
