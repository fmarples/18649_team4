"""Check selected package variants, saved pads and critical pin nets.

Run with KiCad Python. Manufacturer interpretation is in
Critical-package-review.md. This is not a solder-process or thermal approval.
"""
from pathlib import Path
import hashlib
import json
import pcbnew as p

ROOT = Path(__file__).resolve().parent
board_path = ROOT / "KiCad/Lab4.kicad_pcb"
b = p.LoadBoard(str(board_path))
fps = {f.GetReference(): f for f in b.GetFootprints()}
rows = []


def check(ref, value, footprint, expected, coordinates):
    f = fps[ref]
    assert f.GetValue() == value, (ref, f.GetValue())
    assert f.GetFPIDAsString() == footprint, ref
    pads = {a.GetNumber(): a for a in f.Pads() if a.GetNumber()}
    assert set(pads) == set(coordinates), ref
    for n, geometry in coordinates.items():
        a = pads[n]; pos = a.GetFPRelativePosition(); size = a.GetSize()
        actual = [p.ToMM(pos.x), p.ToMM(pos.y), p.ToMM(size.x), p.ToMM(size.y)]
        assert max(abs(x - y) for x, y in zip(actual, geometry)) < 2e-5, (ref, n, actual)
    for n, suffix in expected.items():
        net = pads[n].GetNetname()
        assert (net.startswith("unconnected-") if suffix == "NC" else net.endswith(suffix)), (ref, n, net, suffix)
    rows.append(dict(ref=ref, part=value, footprint=footprint,
                     numbered_pads=len(pads), checked_pin_nets=expected,
                     saved_pad_geometry_mm=coordinates, result="match"))


def dual(count, pitch, row, length, width):
    m = count // 2
    return {str(i + 1): [-row / 2, (i - (m - 1) / 2) * pitch, length, width]
            for i in range(m)} | {
                str(i + m + 1): [row / 2, ((m - 1) / 2 - i) * pitch, length, width]
                for i in range(m)}


for ref in ["U11", "U15", "U21", "U25", "U31", "U35"]:
    check(ref, "SN65HVD231DR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
          {"1": "TXD", "2": "/GND", "3": "/+3V3", "4": "RXD",
           "5": "NC", "6": "L_LOCAL", "7": "H_LOCAL", "8": "/GND"},
          dual(8, 1.27, 4.95, 1.95, .6))
for ref, side in [("U2", "LEFT"), ("U3", "RIGHT")]:
    check(ref, "ACS712ELCTR-05B-T", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
          {"1": f"{side}_BRIDGE", "2": f"{side}_BRIDGE", "3": f"{side}_MOTOR",
           "4": f"{side}_MOTOR", "5": "/GND", "6": f"{side}_FILTER", "7": f"{side}_RAW", "8": "/+5V"},
          dual(8, 1.27, 4.95, 1.95, .6))
check("Q1", "DMPH3010LK3-13", "Package_TO_SOT_SMD:TO-252-2",
      {"1": "RP_GATE", "2": "BAT_FUSED", "3": "/VBAT_PROTECTED"},
      {"1": [-5.04, -2.28, 2.2, 1.2], "2": [1.26, 0, 6.4, 5.8], "3": [-5.04, 2.28, 2.2, 1.2]})
for ref, bus in [("U10", "A"), ("U14", "B"), ("U20", "A"), ("U24", "B"), ("U30", "A"), ("U34", "B")]:
    check(ref, "MCP2515T-I/ST", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
          {"1": "TXD", "2": "RXD", "3": "NC", "4": "/+3V3", "5": "/+3V3", "6": "NC",
           "7": "/+3V3", "8": "OSC2", "9": "OSC1", "10": "/GND", "11": "NC", "12": "NC",
           "13": f"INT_{bus}", "14": "SCK", "15": "NC", "16": "MOSI", "17": "MISO",
           "18": f"CS_{bus}", "19": "RESET", "20": "/+3V3"}, dual(20, .65, 5.725, 1.475, .4))
qfp = {}
for i in range(16):
    d = -3.75 + .5 * i
    qfp[str(i + 1)] = [-5.675, d, 1.55, .3]
    qfp[str(i + 17)] = [d, 5.675, .3, 1.55]
    qfp[str(i + 33)] = [5.675, -d, 1.55, .3]
    qfp[str(i + 49)] = [-d, -5.675, .3, 1.55]
for ref in ["U50", "U60"]:
    check(ref, "STM32F401RET6TR", "Package_QFP:LQFP-64_10x10mm_P0.5mm",
          {**{n: "/+3V3" for n in ["1", "19", "32", "48", "64"]},
           **{n: "/GND" for n in ["12", "18", "31", "47", "63"]},
           "7": "RESET_N", "13": "VDDA", "30": "VCAP1", "46": "SWDIO", "49": "SWCLK", "60": "BOOT0"}, qfp)

# Diodes DS30036: base 1, emitter 2, collector 3. Library SOT23 lands
# cover the specified leads; comparison to the suggested pattern is in the review.
for ref in ["Q550", "Q551", "Q650", "Q651"]:
    check(ref, "MMBT3904", "Package_TO_SOT_SMD:SOT-23",
          {"1": "LED_BASE", "2": "/GND", "3": "LED_SINK"},
          {"1": [-.9375, -.95, 1.475, .6], "2": [-.9375, .95, 1.475, .6],
           "3": [.9375, 0, 1.475, .6]})

# Eaton ELX1097 p.3: 8.5mm outer span, 2.8mm inner gap, 6.6mm land width.
for ref, switch, output in [("L1", "P_SERVO_SW", "/+6V6_SERVO"),
                            ("L2", "P_5V_SW", "/+5V"),
                            ("L3", "P_3V3_SW", "/+3V3")]:
    check(ref, "4.7uH / 5.8A", "Lab4_Power:Eaton_SDCHA1V8040",
          {"1": switch, "2": output},
          {"1": [-2.825, 0, 2.85, 6.6], "2": [2.825, 0, 2.85, 6.6]})

# Hirose EDC-378620-00: 3.96mm pitch, 1.8mm terminal drills, 1.6mm
# guide hole at (-1.5,3.25) in this component-side footprint orientation.
for ref, value, nets in [
        ("J40", "Battery input: 1=+ 2=GND", ["BAT_PLUS", "/GND"]),
        ("J80", "LEFT motor", ["LEFT_MOTOR", "LEFT_RETURN"]),
        ("J81", "RIGHT motor", ["RIGHT_MOTOR", "RIGHT_RETURN"]),
        ("J90", "Servo: GND / 6.6V / PWM", ["/GND", "SERVO_VPLUS", "SERVO_PWM_OUT"])]:
    count = len(nets)
    check(ref, value, f"Connector_Hirose:Hirose_DF63M-{count}P-3.96DSA_1x0{count}_P3.96mm_Vertical",
          {str(i+1): net for i, net in enumerate(nets)},
          {str(i+1): [3.96*i, 0, 2.46, 2.8] for i in range(count)})
    for pad in fps[ref].Pads():
        if pad.GetNumber():
            assert pad.GetAttribute() == p.PAD_ATTRIB_PTH
            assert abs(p.ToMM(pad.GetDrillSize().x)-1.8) < 1e-6
        else:
            assert pad.GetAttribute() == p.PAD_ATTRIB_NPTH
            assert abs(p.ToMM(pad.GetDrillSize().x)-1.6) < 1e-6
            assert abs(p.ToMM(pad.GetFPRelativePosition().x)+1.5) < 1e-6
            assert abs(p.ToMM(pad.GetFPRelativePosition().y)-3.25) < 1e-6
    rows[-1]["terminal_drill_mm"] = 1.8
    rows[-1]["guide_drill_mm"] = 1.6

# Keystone drawing 3568 revision C: 9.92 x 3.40mm pattern; four
# minimum 1.60mm holes. The saved library uses 1.78mm finished drills.
f=fps["F1"]
assert f.GetFPIDAsString() == "Fuse:Fuseholder_Blade_Mini_Keystone_3568"
actual=[]
for pad in f.Pads():
    if not pad.GetNumber(): continue
    x,y=(p.ToMM(pad.GetFPRelativePosition().x),p.ToMM(pad.GetFPRelativePosition().y))
    drill=p.ToMM(pad.GetDrillSize().x)
    assert pad.GetAttribute()==p.PAD_ATTRIB_PTH
    assert abs(drill-1.78)<1e-6 and abs(p.ToMM(pad.GetDrillSize().y)-drill)<1e-6
    assert pad.GetNetname().endswith("BAT_PLUS" if pad.GetNumber()=="1" else "BAT_FUSED")
    actual.append([pad.GetNumber(),round(x,3),round(y,3)])
assert sorted(actual)==[["1",0.,0.],["1",0.,3.4],["2",9.92,0.],["2",9.92,3.4]]
rows.append(dict(ref="F1",part="3568",result="match",saved_drill_mm=1.78,
                 manufacturer_minimum_hole_mm=1.60,saved_pad_positions_mm=actual,
                 source="https://www.keyelco.com/product-pdf.cfm?p=306"))

# Panasonic EEU-FR1E471 is D10 x L12.5mm, with 5mm lead spacing.
# The previous D8/P3.5 footprint was a genuine package mismatch.
check("C802", "470u 25V", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
      {"1": "/VBAT_PROTECTED", "2": "/GND"},
      {"1": [0, 0, 2, 2], "2": [5, 0, 2, 2]})
for pad in fps["C802"].Pads():
    assert pad.GetAttribute() == p.PAD_ATTRIB_PTH
    assert abs(p.ToMM(pad.GetDrillSize().x)-1.0) < 1e-6
rows[-1].update(body_diameter_mm=10, body_length_mm=12.5, lead_pitch_mm=5,
                manufacturer_lead_diameter_mm=.6, saved_drill_mm=1.0)

check("C400", "1000u / 25V", "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm",
      {"1": "/VBAT_PROTECTED", "2": "/GND"},
      {"1": [0, 0, 2.4, 2.4], "2": [5, 0, 2.4, 2.4]})
rows[-1].update(body_diameter_mm=12.5, body_length_mm=20, lead_pitch_mm=5)

# AVX TPS B-case: 3.5 x 2.8mm, 2.1mm maximum height; band marks ANODE.
for ref, positive in [("C804", "/+5V"), ("C805", "ENC_4V")]:
    check(ref, "10u 16V 10% low-ESR", "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B",
          {"1": positive, "2": "/GND"},
          {"1": [-1.54, 0, 1.34, 2.39], "2": [1.54, 0, 1.34, 2.39]})

# SMC N0952 rev.A, SMB terminals. Cathode is pad 1; motor clamps must
# point from ground to each output and from each output to the battery rail.
for i, output in enumerate(["LEFT_BRIDGE", "LEFT_RETURN", "RIGHT_BRIDGE", "RIGHT_RETURN"]):
    for offset, nets in [(0, {"1": "/VBAT_PROTECTED", "2": output}),
                         (1, {"1": output, "2": "/GND"})]:
        check(f"D{800+2*i+offset}", "SK520B", "Diode_SMD:D_SMB", nets,
              {"1": [-2.15, 0, 2.5, 2.3], "2": [2.15, 0, 2.5, 2.3]})

report = dict(source_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
              fabrication_release=False, checked_components=len(rows), results=rows,
              limitations=["Checks only the listed identities, pad coordinates and pin nets.",
                           "Manufacturer lead/pad interpretation is documented separately; no placement, solder, cooling or lifetime qualification is implied.",
                           "MCU checks cover power/reset/boot/debug; GPIO alternate-function review remains in the existing pin-map/routing evidence."],
              sources=["https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf",
                       "https://www.allegromicro.com/-/media/files/datasheets/acs712-datasheet.pdf",
                       "https://www.diodes.com/datasheet/download/DMPH3010LK3.pdf",
                       "https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2515-Family-Data-Sheet-DS20001801K.pdf",
                       "https://www.st.com/resource/en/datasheet/stm32f401re.pdf",
                       "https://www.diodes.com/datasheet/download/MMBT3904.pdf",
                       "https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf",
                       "https://datasheets.kyocera-avx.com/TPS.pdf",
                       "https://www.smc-diodes.com/propdf/SK520B%20N0952%20REV.A.pdf",
                       "https://www.hirose.com/en/product/p/CL0680-0567-0-00",
                       "https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf"])
(ROOT / "Selected-package-check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"PASS: {len(rows)} selected components; saved pad geometry and critical pin nets match")
