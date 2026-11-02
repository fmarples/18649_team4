# Schematic presentation — November 2

We matched the visual organization of Tom's schematic PDF posted in the
[staff reference message](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793596091232639).
This is a presentation update to the November 2 Anson-review revision `7644128`.

- Added native blue dashed frames and bold headings around functional sections.
- Stacked each zone's CAN A and CAN B blocks; grouped MCU, actuator, current-sense,
  encoder, lamp and test-header circuits under separate headings.
- Grouped the Pi interface, status LEDs and test headers on the cockpit sheet.
- Framed the battery input and each supply rail on the power sheet, and grouped
  the hierarchy and design notes on the overview sheet.
- Corrected upside-down part text, moved the Pi-header and fuse fields for
  readability, and standardized title blocks and note sizes.
- Exported a white-background, five-page vector PDF. The frames and headings
  are editable in the native schematics, not overlays applied only to the PDF.

We compared the result against `7644128`: all 300 component identities and
1,077 pin-to-net assignments are unchanged. Symbol libraries, part properties,
and hierarchical interfaces are unchanged. The PCB, Gerbers, placement files,
BOM and report are byte-identical to that revision.

Fresh KiCad ERC, DRC, schematic-to-PCB parity and unconnected checks report
zero findings. All five rendered circuit sheets were visually reviewed.
[Schematic-format-check.json](Schematic-format-check.json) records the comparison
and current source hashes. This formatting change does not change the operating
assumptions or imply powered validation or fabrication approval.
