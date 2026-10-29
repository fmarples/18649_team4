# Specialty-parts BOM

28 October 2026. [TEAM_4_BOM_Lab4.xlsx](TEAM_4_BOM_Lab4.xlsx) separates
specialty and common parts for the
[staff purchasing request](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793052274317539).
The workbook contains 57 consolidated specialty lines and 35 common lines.

We compared [Preliminary-BOM.csv](Preliminary-BOM.csv) with
[Course-stock-v3.csv](Course-stock-v3.csv). An exact listed MPN is common.
The course's generic 2.54 mm header entry also covers the specified pin-header
rows; their row/pin geometry and allocated quantities still need confirmation.
Every other requested part is marked specialty, including same-function parts
with a different MPN. The exact Samtec Pi socket is a specialty part.
The [course-list clarification](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792789284321879)
identifies v3 as the parts on hand, with front current sensing and standoffs
among the additions teams must choose.

We consolidated matching part/specification, footprint and unit entries,
summing design quantities, off-board quantities and proposed spares without
changing total demand. All 127 active CSV rows appear once in the workbook;
ten zero-quantity historical alternatives are omitted. Wire quantities remain
metres. The U81 purchasing line uses the already reviewed SN74LVC14APW
carrier alternative, with the schematic's PWR code explained alongside it.

Yellow rows on the first sheet identify specialty parts. The second sheet
contains common parts. Each line includes a source link, quantities,
references, footprint and purchasing notes. Common-list membership does not
establish the quantity allocated to our team. Request only the shortfall
after checking course/team stock; the totals already include proposed spares.

The TA-approved CNHL S220403BK battery and Hitec 44295 charger replace the
active NiMH options; Amazon is permitted for both. One battery listing is a
two-pack (one fitted, one spare), not two listings. New monitor, XT60 and
inline-fuse parts are included. The shorter Pi socket, encoder supply and
precision-resistor changes and revised capacitor banks/feed-forward parts are reconciled. Remaining course allocations,
servo-side lead, fuse coordination and bag supply
are flagged. Supplier selection is not a purchase or stock reservation.

Checks: all source rows and quantity totals reconcile; formula cached values,
native supplier/source hyperlinks, filter tables and frozen headings were
verified in the saved Excel file. Both sheets were visually inspected.
[Specialty-BOM-check.json](Specialty-BOM-check.json) records source hashes,
source-row mappings and the workbook hash.

The requested destination is the
[course BOM folder](https://drive.google.com/drive/folders/15MCRrvGx3S5bV2gtYmitpYQ7jAbZF8_f).
We updated the existing Excel file in place on October 28, 2026 at 20:01 EDT.
The [Drive workbook](https://docs.google.com/spreadsheets/d/1jn-2KS-h_1bZtQV-ySlfCStYBRyWNMzS/edit)
retains its original ID and both sheets. The readback is 24,720 bytes and its
SHA-256 exactly matches the local workbook. The active CSV is the editable
source; future circuit changes must be reconciled again before ordering.
No additional archive, purchase, or notification was made.
