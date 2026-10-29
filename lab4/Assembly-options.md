# Assembly options for the same Lab 4 design

## Current assembly decisions — October 29

We will assemble the SMT parts first and install the through-hole Pi socket,
power connectors, electrolytics and heatsink hardware afterward. No new
footprint or paste aperture is required by the package review below. The
actual solder alloy, stencil and temperature profile must be chosen with the
course assembly facility before assembly; this is not a request for chassis
measurements or a claim that a generic reflow profile has been qualified.

- **J70:** keep ESQ-118-44-L-D out of the lead-free SMT reflow cycle. Its
  [exact family catalog](https://suddendocs.samtec.com/catalog_english/esq_th.pdf)
  specifies lead wave only. Samtec's general wave note is not a hand-iron
  specification. Before soldering, obtain a suitable localized process from
  the course assembler/Samtec, or review a documented replacement. Do not
  import a profile for a different ESQ lead style or restore the 40-pin part.
- **L1–L3:** [Eaton ELX1097, p. 3](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf)
  recommends at least 0.15 mm paste thickness. Agree on a local step-up/paste
  deposition process or a separately controlled inductor installation with
  the assembler. Do not increase the whole stencil thickness just to satisfy
  these three parts without checking the fine-pitch SOT-563 apertures. The
  current Gerber apertures are geometry, not proof of deposited paste volume.
- **Hirose headers and harnesses:** the [DF63 catalog](https://www.hirose.com/en/product/series/DF63/documents?path=/api/v1/series/DF63/documents/product_series_catalog/content?lang%3DEN)
  gives straight-header manual soldering at 290 °C for 3 seconds and flow at
  260 °C for 5 seconds. Harness contacts are crimped with the matching wire
  and tooling; XT60 solder cups and insulated wire transitions are soldered.
  Wire gauge alone does not establish the crimp: check insulation diameter,
  strand construction and the contact's crimp-condition table.

The three-position DF63 servo interface is rated 7 A with 22 AWG under the
catalog conditions; that does not qualify the unknown factory servo mate or
the proposed 26 AWG donor lead. We therefore keep that donor conditional.
Researching a higher-rated male header alone cannot establish the rating of
the complete mated connection. An accepted servo lead or a reviewed splice
to the factory cable is still needed; finished fit and continuity checks
follow assembly. See [Actuator-design.md](Actuator-design.md).

The [expanded package audit](Critical-package-review.md) passes for 186
components. It does not approve the above manufacturing processes. The team
does not need to repeat the completed hole, cable-photo or paper-fit work.

## Earlier revision — October 27

The [mounting and encoder revision](Mounting-and-encoder-revision.md) supersedes
older socket, heatsink-placement and encoder-voltage statements below. All
eight supports now meet the 3 mm hole-edge rule; HS80 is installed; encoders
have a separate 4.0 V supply. Current JSON checks carry the active board hash.
Battery/protection, Pi voltage margin and exact capacitor data remain open.

## Earlier review record


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

The selected J70 is Samtec ESQ-118-44-L-D, 36 contacts mating Pi pins 3–38. The current
[ESQ through-hole catalog](https://suddendocs.samtec.com/catalog_english/esq_th.pdf)
marks lead-free solderability as unavailable and specifies lead wave only.
Do not assume it may accompany the SMT parts through a lead-free reflow cycle.
Plan to install it after the SMT thermal cycle, using a hand-solder process
confirmed suitable for this exact connector by Samtec/course staff, or select
a mechanically compatible connector with documented process limits. This is
an assembly-process check. The saved shortened-socket placement check covers
Pi pins 3–38; the old forty-contact socket must not be substituted.
