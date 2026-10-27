# Assembly options for the same Lab 4 design

23 October 2026, updated after the TA reply. The course will have teams assemble
all SMD parts themselves. TechSpark oven access is tentative. We therefore
use **BOM-Hand-assembly.csv** as the active assembly list and course v3 stock
as the first source. Additional purchases stay in Preliminary-BOM.csv.
The JLC list below is a historical catalog comparison, not an assembly request
or a second circuit. It does not create a JLC quote task for October 24.
[TA assembly reply](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1792811196129409?thread_ts=1792803278.879979&cid=C0BRYGTD4HH).

| | Team assembly | JLCPCB plus team assembly |
|---|---|---|
| Parts list | BOM-Hand-assembly.csv | BOM-JLC-hybrid.csv |
| Small surface-mount parts | Team solders/reflows all parts | Request top-side SMT assembly for supported, verified parts |
| Through-hole and underside parts | Team installs them | Request JLC assembly where eligible; obtain an exact-parts/process quote, including the underside Pi socket |
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

A library match does not reserve stock. ST lists RET6TR as tape/reel and RET6
as tray, with the same LQFP64 device/package. We verified this carrier-only
alternative and record STM32F401RET6 / C116978 in JLC_selected_MPN; the schematic
keeps the course-stock RET6TR code. [ST tray part](https://estore.st.com/en/stm32f401ret6-cpn.html),
[ST tape/reel part](https://estore.st.com/en/stm32f401ret6tr-cpn.html).

Additional exact catalog matches:

| MPN | JLC code | Source |
|---|---|---|
| MCP2515T-I/ST | C185941 | [TSSOP-20](https://jlcpcb.com/partdetail/MicrochipTech-MCP2515T_IST/C185941) |
| WSL2512R0100FEA | C844901 | [10 mΩ / 1 W / 1%](https://jlcpcb.com/partdetail/VishayIntertech-WSL2512R0100FEA/C844901) |
| MMBT3904-7-F | C94514 | [Diodes Incorporated SOT-23](https://jlcpcb.com/partdetail/DiodesIncorporated-MMBT3904_7F/C94514) |
| ACS712ELCTR-05B-T | C44471 | [Allegro part](https://jlcpcb.com/partdetail/45473-ACS712ELCTR_05BT/C44471) |
| L298N | C19922 | [ST Multiwatt-15 identity; assembly availability unconfirmed](https://jlcpcb.com/partdetail/STMicroelectronics-L298N/C19922) |

Other unmatched lines remain explicit. Do not substitute the similarly named
XBLW current sensor for Allegro without reviewing its specifications and package.

JLCPCB supports eligible through-hole parts. Its guidance says two-sided
placement requires Standard PCBA, including a through-hole part on the opposite
side. Compare a quote including J70 against fitting that one socket ourselves.
The latter is a fallback, not a requirement that all connectors be hand-soldered.
[JLCPCB assembly guidance](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype).

The course assembly decision supersedes our earlier preference for maximum
JLCPCB assembly. Battery, charger, cables, crimps, standoffs and vehicle/heatsink
installation also require team work. No stock has been reserved or ordered.
The table above preserves the researched alternative only. For the current
purchase request, use the hand-assembly BOM plus external items in the
combined BOM. Confirm the stencil/paste/reflow arrangement with the course
before assembly; it is not a prerequisite to submitting the schematic.

## Pi socket process note — October 27

The selected J70 is Samtec ESQ-120-44-L-D. The current
[ESQ through-hole catalog](https://suddendocs.samtec.com/catalog_english/esq_th.pdf)
marks lead-free solderability as unavailable and specifies lead wave only.
Do not assume it may accompany the SMT parts through a lead-free reflow cycle.
Plan to install it after the SMT thermal cycle, using a hand-solder process
confirmed suitable for this exact connector by Samtec/course staff, or select
a mechanically compatible connector with documented process limits. This is
an assembly-process check; the saved forty-pin placement check remains valid.
