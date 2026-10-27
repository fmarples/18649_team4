# Specialty-parts BOM

26 October 2026. [TEAM_4_BOM_Lab4.xlsx](TEAM_4_BOM_Lab4.xlsx) separates
specialty and common parts for the
[staff purchasing request](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793052274317539).
The workbook contains 49 consolidated specialty lines and 36 common lines.

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
changing total demand. All 121 active CSV rows appear once in the workbook;
six zero-quantity historical alternatives are omitted. Wire quantities remain
metres. The U81 purchasing line uses the already reviewed SN74LVC14APW
carrier alternative, with the schematic's PWR code explained alongside it.

Yellow rows on the first sheet identify specialty parts. The second sheet
contains common parts. Each line includes a source link, quantities,
references, footprint and purchasing notes. Common-list membership does not
establish the quantity allocated to our team. Request only the shortfall
after checking course/team stock; the totals already include proposed spares.

The provisional battery, charger, servo-side lead, heatsink attachment and
fuse qualification remain open in the workbook. No new part selection or
stock reservation is established by this classification. The workbook is a
formatted purchasing snapshot; the CSV remains the editable source and must
be reconciled when selections change.

Checks: all source rows and quantity totals reconcile; formula cached values,
native supplier/source hyperlinks, filter tables and frozen headings were
verified in the saved Excel file. Both sheets were visually inspected.
[Specialty-BOM-check.json](Specialty-BOM-check.json) records source hashes,
source-row mappings and the workbook hash.

The requested destination is the
[course BOM folder](https://drive.google.com/drive/folders/15MCRrvGx3S5bV2gtYmitpYQ7jAbZF8_f).
We uploaded the Excel file on October 26, 2026 at 9:51 p.m. EDT.
The folder listing confirms the filename, Excel format and 20,471-byte size.
The [uploaded workbook](https://docs.google.com/spreadsheets/d/1jn-2KS-h_1bZtQV-ySlfCStYBRyWNMzS/edit?usp=drivesdk&ouid=101000648938892436394&rtpof=true&sd=true)
contains the reviewed file from revision da8d5e6. The upload record is included
in Specialty-BOM-check.json; open purchasing selections remain identified in
the workbook.
