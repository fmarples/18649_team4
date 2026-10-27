"""Review buck-divider arithmetic and saved placement; run with KiCad Python.

Connectivity is independently checked by check_netlist.py. This report does
not establish routed-loop quality, effective capacitance or thermal capability.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import pcbnew as p

ROOT = Path(__file__).resolve().parent
with (ROOT/'KiCad/Circuit-BOM.csv').open(encoding='utf-8-sig', newline='') as f:
    parts = {r['Reference']: r for r in csv.DictReader(f)}
design = json.loads((ROOT/'Power-calculations.json').read_text(encoding='utf-8'))
board = p.LoadBoard(str(ROOT/'KiCad/Lab4.kicad_pcb'))
fps = {f.GetReference(): f for f in board.GetFootprints()}


def resistance(ref):
    value = parts[ref]['Value'].split()[0]
    return float(value[:-1])*1000 if value.endswith('k') else float(value)


def point(ref, number):
    pad = next(a for a in fps[ref].Pads() if a.GetNumber() == str(number))
    pos = pad.GetPosition()
    return (p.ToMM(pos.x), p.ToMM(pos.y))


def distance(a, b):
    return round(math.dist(point(*a), point(*b)), 3)


rows = []
for i, allocation in enumerate(design['regulators']):
    u, ind, base = f'U{40+i}', f'L{i+1}', 410+10*i
    top, bottom = resistance(f'R{base}'), resistance(f'R{base+1}')
    assert parts[u]['MPN'] == 'TPS564252DRLR'
    assert parts[ind]['MPN'] == 'SDCHA1V8040-4R7-R'
    tolerance = .001 if i == 1 else .01
    for ref in [f'R{base}', f'R{base+1}']:
        assert ('0.1%' if i == 1 else '1%') in parts[ref]['Value'], ref
    nominal = .6*(1+top/bottom)
    assert abs(nominal-allocation['voltage']) < 1e-9
    low = .591*(1+top*(1-tolerance)/(bottom*(1+tolerance)))
    high = .609*(1+top*(1+tolerance)/(bottom*(1-tolerance)))
    en_top, en_bottom = resistance(f'R{base+2}'), resistance(f'R{base+3}')
    en_parallel_typ = 1/(1/en_bottom+1/2e6)
    en_rising_typ = 1.19*(1+en_top/en_parallel_typ)
    # Ignoring the internal pulldown maximizes EN voltage; use 1% external
    # resistor corners. Its unspecified tolerance prevents guaranteed UVLO bounds.
    vin_max = design['protected_input_design_range_V'][1]
    en_max = vin_max*en_bottom*1.01/(en_top*.99+en_bottom*1.01)
    assert en_max < 5.5, (u, 'EN exceeds recommended maximum')
    inductance = allocation['inductance_uH']*1e-6*.8
    ripple = nominal*(vin_max-nominal)/(vin_max*inductance*600000)
    load = allocation['allocation_A']
    peak = load+ripple/2
    rms = math.sqrt(load**2+ripple**2/12)
    assert peak < 6.7 and rms < 5.8, (u, 'allocated-load inductor check')
    for ref in (f'C{base+2}', f'C{base+3}'):
        assert parts[ref]['MPN'] == 'GRM219R61C226ME15L', ref
    # TI Eq. 4 uses effective capacitance. These are sensitivity cases,
    # not claimed DC-bias/temperature characteristics of the selected MLCC.
    nominal_l = allocation['inductance_uH']*1e-6
    filter_cases = []
    for effective_uF in (44, 33, 22, 16.84, 11):
        filter_cases.append({
            'assumed_total_effective_capacitance_uF': effective_uF,
            'LC_pole_kHz_nominal_L': round(1/(2*math.pi*math.sqrt(
                nominal_l*effective_uF*1e-6))/1000, 3),
            'LC_pole_kHz_minus20percent_L': round(1/(2*math.pi*math.sqrt(
                inductance*effective_uF*1e-6))/1000, 3)})
    # Physical orientation check: a direct SW-to-L route must depart the
    # power side, rather than cross the device toward its feedback pins.
    sw, fb, l_in = point(u, 2), point(u, 6), point(ind, 1)
    assert sw[0] > fb[0] and l_in[0] > sw[0], (u, 'SW faces away from inductor')
    rows.append({
        'reference': u, 'rail': allocation['rail'],
        'output_nominal_V': round(nominal, 6),
        'static_reference_and_resistor_corners_V': [round(low, 6), round(high, 6)],
        'feedback_resistor_tolerance_percent': tolerance*100,
        'EN_rising_typical_V': round(en_rising_typ, 6),
        'EN_max_at_15V_1percent_external_resistors_no_internal_pulldown_V': round(en_max, 6),
        'allocated_output_A': load,
        'inductor_at_minus20percent_L_600kHz': {
            'ripple_A_pp': round(ripple, 6), 'peak_A': round(peak, 6),
            'rms_A': round(rms, 6)},
        'output_filter_sensitivity_not_qualification': {
            'nominal_total_capacitance_uF': 44,
            'effective_capacitance_for_20kHz_pole_at_minus20percent_L_uF':
                round(1/((2*math.pi*20000)**2*inductance)*1e6, 3),
            'cases': filter_cases},
        'pad_center_distances_mm_not_routed_lengths': {
            'SW_to_inductor': distance((u, 2), (ind, 1)),
            'VIN_to_100nF': distance((u, 1), (f'C{base+1}', 1)),
            'FB_to_top_resistor': distance((u, 6), (f'R{base}', 2)),
            'inductor_output_to_nearest_22uF': min(
                distance((ind, 2), (f'C{base+2}', 1)),
                distance((ind, 2), (f'C{base+3}', 1)))},
    })

report = {
    'status': 'PASS for stated calculations and placement orientation only',
    'fabrication_release': False,
    'sources': [
        'https://www.ti.com/lit/ds/symlink/tps564252.pdf',
        'https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf'],
    'regulators': rows,
    'limitations': [
        '600kHz and the internal 2Mohm EN pulldown are typical, not guaranteed bounds.',
        'Static output corners omit wiring drop, load/line regulation, ripple and transients.',
        'Inductor check uses allocated load, -20% inductance and nominal output voltage; not a full fault/temperature/frequency bound.',
        'A 6.7A saturation rating does not cover worst-case 6.7A valley current limit plus ripple.',
        '44uF output is nominal; manufacturer DC-bias/temperature data and loop review remain needed.',
        'TI effective thermal data uses a 2oz EVM; our 1oz board has no validated thermal rating.',
        'Initial local regulator tracks and ground vias exist; Kelvin return, loop quality and hardware behavior still need review.',
        'EN thresholds are not a NiMH battery cutoff or proof of regulation at turn-on.'],
    'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                      for name in ['KiCad/Lab4.kicad_pcb', 'KiCad/Power.kicad_sch',
                                   'KiCad/Circuit-BOM.csv', 'Power-calculations.json']},
}
(ROOT/'Power-stage-check.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
