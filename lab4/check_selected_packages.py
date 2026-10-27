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

report = dict(source_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
              fabrication_release=False, checked_components=len(rows), results=rows,
              limitations=["Checks only the listed identities, pad coordinates and pin nets.",
                           "Manufacturer lead/pad interpretation is documented separately; no placement, solder, cooling or lifetime qualification is implied.",
                           "MCU checks cover power/reset/boot/debug; GPIO alternate-function review remains in the existing pin-map/routing evidence."],
              sources=["https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf",
                       "https://www.allegromicro.com/-/media/files/datasheets/acs712-datasheet.pdf",
                       "https://www.diodes.com/datasheet/download/DMPH3010LK3.pdf",
                       "https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2515-Family-Data-Sheet-DS20001801K.pdf",
                       "https://www.st.com/resource/en/datasheet/stm32f401re.pdf"])
(ROOT / "Selected-package-check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"PASS: {len(rows)} selected components; saved pad geometry and critical pin nets match")
