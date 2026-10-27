"""Nominal dimensional checks from the saved PCB and documented team evidence.

Run with KiCad Python. This does not assert an assembled fit or a complete
vehicle sweep. Sources, assumptions and the distinction are in Mechanical-evidence.md.
"""
import hashlib
import json
import math
from pathlib import Path
import pcbnew as p

ROOT = Path(__file__).resolve().parent
board_path = ROOT / 'KiCad/Lab4.kicad_pcb'
b = p.LoadBoard(str(board_path))
data = json.loads((ROOT/'placement-data.json').read_text(encoding='utf-8'))
pi = data['pi']
fps = {f.GetReference(): f for f in b.GetFootprints()}
socket = fps['J70']
# Use the actual body drawing, excluding its graphic stroke width/courtyard.
body = [g for g in socket.GraphicalItems()
        if g.GetLayer() == p.B_Fab and g.GetShape() == p.SHAPE_T_RECT]
assert len(body) == 1, 'Expected one bottom-side socket body rectangle'
a, z = body[0].GetStart(), body[0].GetEnd()
x0, x1 = sorted([p.ToMM(a.x), p.ToMM(z.x)])
y0, y1 = sorted([p.ToMM(a.y), p.ToMM(z.y)])
support_distances = []
for ref in ['H5', 'H6', 'H7', 'H8']:
    hole = fps[ref]
    q = hole.GetPosition()
    x, y = p.ToMM(q.x), p.ToMM(q.y)
    pad = next(iter(hole.Pads()))
    drill = p.ToMM(pad.GetDrillSize().x)
    distance = math.hypot(max(x0-x, 0, x-x1), max(y0-y, 0, y-y1))
    support_distances.append(dict(reference=ref, drill_mm=drill,
        center_to_socket_body_mm=round(distance, 4),
        hole_edge_to_socket_body_mm=round(distance-drill/2, 4),
        hardware_to_socket_mm=round(distance-pi['support_max_od_mm']/2, 4),
        strict_3mm_hole_edge_margin_shortfall_mm=round(max(0, 3+drill/2-distance), 4)))

gap = pi['board_gap_mm']
tail_limit = 3.0  # Assembly specification, not a measured installed tail.
underside = pi['main_pcb_chassis_gap_mm'] - gap - pi['pi_thickness_assumed_mm']
insertion = pi['gpio_tip_height_mm'] - (gap-pi['socket_body_height_mm'])
# These recorded dimensions are nominal. The additional 5 mm case is a
# sensitivity allowance, not an independently established tolerance bound.
wheel_diameter = 75.0  # User-reported in doc/HARDWARE.md.
plate_gap = 51.75  # October 24 team report, Mechanical-evidence.md.
wheel_clearance = plate_gap + pi['main_pcb_chassis_gap_mm'] - tail_limit - wheel_diameter
results = dict(
    status='NOMINAL_CALCULATIONS_COMPLETE_NOT_ASSEMBLY_QUALIFICATION',
    pcb_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
    pi_stack_mm=dict(chassis_gap=pi['main_pcb_chassis_gap_mm'], pi_gap=gap,
        pi_underside_above_chassis=round(underside, 3),
        underside_clearance_after_5mm_envelope=round(underside-5, 3),
        usb_clearance_after_3mm_tails=round(gap-pi['usb_height_mm']-tail_limit, 3),
        conservative_18mm_top_envelope_clearance=round(gap-18-tail_limit, 3),
        socket_insertion=round(insertion, 3),
        insertion_lower_margin=round(insertion-pi['header_insertion_min_mm'], 3),
        insertion_upper_margin=round(pi['header_insertion_max_mm']-insertion, 3)),
    socket_body_absolute_mm=[x0, y0, x1, y1],
    pi_supports=support_distances,
    main_board_wheel_vertical_screen_mm=dict(wheel_diameter_reported=wheel_diameter,
        interplate_height_reported=plate_gap,
        pcb_tail_to_tire_clearance_lower_bound_under_model=round(wheel_clearance, 3),
        additional_unverified_height_allowance=5.0,
        clearance_with_that_allowance=round(wheel_clearance-5, 3)),
    port_envelope_limits_mm=dict(
        top_side_plug_or_cooler_height_max_with_1mm_margin=gap-tail_limit-1,
        pi_usb_ethernet_board_edge_recess=data['width_mm']-pi['x_mm']-pi['width_mm'],
        pi_microsd_board_edge_recess=pi['x_mm']),
    limits=[
        'Drawing-based calculation, not a new physical measurement.',
        'Wheel calculation assumes upright tires on a level surface and a rigid chassis; lower plate ground clearance is conservatively taken as zero.',
        'Wheel result applies to the main PCB and <=3 mm downward tails, not the lower Pi, chassis spacers, loose cables, obstacles or unspecified camber.',
        'Complete horizontal wheel sweep is not established without pivot/stop geometry; retain full-steering inspection as an unpowered assembly check.',
        'Plug/cooler envelopes are selection limits, not proof that an unspecified accessory fits.',
        'User-directed 3mm clearance from finished hole edge applies to components and copper at every chassis/Pi support.',
        'Engagement, fastener retention, continuity and powered behavior require the assembled hardware.',
    ])
assert pi['header_insertion_min_mm'] <= insertion <= pi['header_insertion_max_mm']
assert min(s['hardware_to_socket_mm'] for s in support_distances) > 0
assert min(s['hole_edge_to_socket_body_mm'] for s in support_distances) >= 3
assert results['pi_stack_mm']['conservative_18mm_top_envelope_clearance'] >= 1
(ROOT/'Mechanical-fit-check.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
print(json.dumps(results, indent=2))
