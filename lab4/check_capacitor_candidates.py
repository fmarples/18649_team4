"""Compare unselected MLCC candidates using Wurth ANP114 equations 3--5.

These fitted typical curves do not guarantee capacitance, ESR or stability.
Run with ordinary Python. Does not change the BOM or PCB.
"""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent
SOURCE = "https://www.we-online.com/components/media/o753710v410%20ANP114a_Polarization%20DC%20Bias%20MLCC_EN.pdf"
# Table 2: capacitance data fitted in nF, voltage in V. Recover Cs/a* in
# nF using the table's scaling, checked against a*=a+Cs*(h/10-1).
MODELS = [
    dict(mpn="885012108018", package="1206", a=22000., cs=3544.,
         h=7.84, b=7.44, vmax=16., tabulated_astar_nF=21234.6),
    dict(mpn="885012109010", package="1210", a=22000., cs=11252.3,
         h=29.51, b=25.43, vmax=16., tabulated_astar_nF=43952.8),
]


def capacitance_uF(model, voltage):
    """Preheated/pristine-sample model, Vc=0; ANP114 equations 3--5."""
    a, cs, h, b, vmax = (model[k] for k in ("a", "cs", "h", "b", "vmax"))
    sech2 = lambda x: 1 / math.cosh(x)**2
    astar = a + cs * (h / 10 - 1)
    a0 = 1 + 2*b/30*sech2(vmax/(16*b))
    cp = astar/a0 * (sech2(10*voltage/(7*b)) +
        b/30*sech2((voltage-vmax/8)/(2*b)) +
        b/30*sech2((voltage+vmax/8)/(2*b))) - cs*h/10
    return (cp + cs)/1000


def calculate():
    rows = []
    for model in MODELS:
        # Independent algebraic normalization/table checks catch unit errors.
        assert math.isclose(capacitance_uF(model, 0), 22, abs_tol=1e-10)
        astar = model["a"] + model["cs"]*(model["h"]/10-1)
        assert abs(astar-model["tabulated_astar_nF"]) < 1
        values = []
        for voltage in (3.37, 5.19, 6.82):
            typical = capacitance_uF(model, voltage)
            # Explicit sensitivities; multiplying these effects is not a
            # manufacturer's guaranteed combined minimum or life limit.
            sensitivity = 2*typical*.8*.85*.8
            values.append(dict(voltage_V=voltage, typical_per_part_uF=typical,
                two_parts_minus20percent_tol_minus15percent_temp_minus20percent_aging_uF=sensitivity,
                LC_kHz_at_3p76uH=1/(2*math.pi*math.sqrt(3.76e-6*sensitivity*1e-6))/1000,
                LC_kHz_at_2p63uH=1/(2*math.pi*math.sqrt(2.63e-6*sensitivity*1e-6))/1000))
        rows.append(dict(**model, cases=values))
    return dict(status="candidate comparison only; no part selected", source=SOURCE,
        source_locations="Equations 3--5, pp.4--5; Table 2, p.10; nF/V explanation p.9",
        unchanged_selected_output_part="GRM219R61C226ME15L",
        fabrication_release=False, results=rows,
        limitations=[
            "Fitted typical C(V) curves at the manufacturer's conditions, not production/temperature/aging guarantees.",
            "20% aging is an explicit sensitivity motivated by the note's general discussion, not an exact-part guaranteed bound.",
            "No ESR, capacitor heating, complete converter loop or load-transient qualification is implied.",
            "Both candidates need larger footprints than the selected 0805 output capacitors and verified purchasing availability.",
            "16V output candidates are not selected replacements for the 25V input capacitor; input-capacitance evidence remains open.",
            "LC pole near 20kHz is design guidance, not a pass/fail stability boundary."])


if __name__ == "__main__":
    report = calculate()
    (ROOT/"Capacitor-candidate-check.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    for row in report["results"]:
        print(row["mpn"], [(x["voltage_V"], round(x["typical_per_part_uF"], 3)) for x in row["cases"]])
