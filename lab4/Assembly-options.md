# Assembly options for the same Lab 4 design

23 October 2026. We have not chosen an assembly service. Both lists use the
same schematic references and quantities; they are not two circuit variants.
The combined `Preliminary-BOM.csv` also includes external wiring, battery,
charger, heatsink and mounting hardware. Those items are needed in either option.

| | Team assembly | JLCPCB plus team assembly |
|---|---|---|
| Parts list | BOM-Hand-assembly.csv | BOM-JLC-hybrid.csv |
| Small surface-mount parts | Team solders/reflows all parts | Request top-side SMT assembly for supported, verified parts |
| Through-hole and underside parts | Team installs them | Team installs L298, socket, connectors, fuse hardware and remaining through-hole parts |
| External wiring and mechanics | Team | Team |
| Main constraint | LQFP/TSSOP and especially SOT-563 require suitable reflow/rework equipment and inspection | Staff approval, service quote, exact library matches, stock and lead time |

For hand assembly, we should plan stencil/paste or controlled hot-air/reflow for
the small buck ICs and crystals, plus magnification and continuity checks. An
ordinary iron alone is not an adequate assembly plan for every package here.
The spare column is a proposed hand-rework allowance, not a factory attrition count.

For hybrid assembly, we verified these library identities on 23 October:

| MPN | JLC code | Source |
|---|---|---|
| TPS564252DRLR | C19191267 | [JLC part](https://jlcpcb.com/partdetail/TexasInstruments-TPS564252DRLR/C19191267) |
| SN65HVD231DR | C129257 | [JLC part](https://jlcpcb.com/partdetail/TexasInstruments-SN65HVD231DR/C129257) |
| SN74LVC14APWR | C7663 | [JLC part](https://jlcpcb.com/partdetail/TexasInstruments-SN74LVC14APWR/C7663) |
| INA180A2IDBVR | C192764 | [JLC part](https://jlcpcb.com/partdetail/TexasInstruments-INA180A2IDBVR/C192764) |

A library match does not reserve stock or approve a substitution. The MCU listing
C116978 identifies STM32F401RET6; our BOM specifies RET6TR, so we have not silently
treated it as an exact ordering-code match. We still need package/carrier review.
Every other unmatched line remains explicit in the hybrid BOM.

After routing and design review, export the final factory BOM and component
position list from that same board revision. Review all polarities, rotations,
bottom-side parts and DNP choices in the assembly preview. Neither current CSV
is a ready-to-order upload. [JLC BOM requirements](https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly).
