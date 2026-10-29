"""Verify the implemented 6396BG / L298N drawing-based mounting.

Run with KiCad Python. Dimensions/datums and limitations are explained in
Heatsink-mounting-review.md. Bounding boxes screen clearance; they do not
assert physical collision with every fin. The active footprint, reserved metal space and pad locations are checked.
"""
import hashlib
import html
import json
from pathlib import Path
import pcbnew as p

ROOT = Path(__file__).resolve().parent
board_file = ROOT / 'KiCad/Lab4.kicad_pcb'
b = p.LoadBoard(str(board_file))
lib = ROOT / 'KiCad/Lab4_Mechanical.pretty'
mount = p.FootprintLoad(str(lib), 'Boyd_6396BG_StraightPins')
assert mount is not None
anchor_pads = sorted(mount.Pads(), key=lambda pad: pad.GetNumber())
assert len(anchor_pads) == 2
for pad, x in zip(anchor_pads, [-12.7, 12.7]):
    assert abs(p.ToMM(pad.GetPosition().x) - x) < 1e-6
    assert abs(p.ToMM(pad.GetPosition().y)) < 1e-6
    assert abs(p.ToMM(pad.GetDrillSize().x) - 2.89) < 1e-6
    assert abs(p.ToMM(pad.GetSize().x) - 4.5) < 1e-6
mount.BuildCourtyardCaches()
assert mount.GetCourtyard(p.F_CrtYd).OutlineCount() == 1
fps = {f.GetReference(): f for f in b.GetFootprints()}
u = fps['U80']
assert u.GetValue() == 'L298N'
assert u.GetOrientationDegrees() == 0 and not u.IsFlipped()
assert u.GetFPIDAsString() == 'Lab4_Power:ST_L298N_Multiwatt15V_D1.1'
mm = p.ToMM
ox, oy = mm(u.GetPosition().x), mm(u.GetPosition().y)
# F.Fab back of metal tab is 9.58 mm behind odd-numbered lead row.
# Even-numbered row is 5.08 mm behind it; drawing M is 4.55 nominal.
cx, face_y = ox + 8.89, oy - 9.58
row_y = face_y - 1.57 / 2
pins = [[cx - 12.7, row_y], [cx + 12.7, row_y]]
rect = [cx - 41.91 / 2, row_y - 25.4 / 2, 41.91, 25.4]
# Conservative solid blocks enclose the fins and anchor barrels. The open
# channel is NOT filled: it deliberately accommodates U80. 2.67 is used as
# an anchor-barrel envelope from the current family drawing, not a PCB drill.
barrel_r = 2.67 / 2
left_end, right_start = pins[0][0] + barrel_r, pins[1][0] - barrel_r
solids = [
    [rect[0], rect[1], left_end - rect[0], rect[3]],
    [right_start, rect[1], rect[0] + rect[2] - right_start, rect[3]],
    [left_end, face_y - 1.57, right_start - left_end, 1.57],
]


def bbox(fp):
    fp.BuildCourtyardCaches()
    bb = fp.GetCourtyard(p.F_CrtYd).BBox()
    return [mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetWidth()), mm(bb.GetHeight())]


def intersects(a, c, margin=0):
    x, y, w, h = a; q, r, s, t = c
    return min(x+w+margin, q+s) > max(x-margin, q)+.001 and min(y+h+margin, r+t) > max(y-margin, r)+.001


boxes = {r: bbox(f) for r, f in fps.items() if not f.IsFlipped()}
outer_hits = sorted(r for r, v in boxes.items() if r != 'U80' and intersects(rect, v))
solid_hits = sorted(r for r, v in boxes.items() if r != 'U80' and any(intersects(s, v, .5) for s in solids))

# Check the installed anchors and drawing-to-device relationship.
hs=fps['HS80']; assert hs.GetFPIDAsString()=='Lab4_Mechanical:Boyd_6396BG_StraightPins'
assert hs.GetAttributes() & p.FP_BOARD_ONLY
for pad,expected in zip(sorted(hs.Pads(),key=lambda a:a.GetNumber()),pins):
    actual=[mm(pad.GetPosition().x),mm(pad.GetPosition().y)]
    assert max(abs(x-y) for x,y in zip(actual,expected))<1e-5
    assert abs(mm(pad.GetDrillSize().x)-2.89)<1e-6
    assert abs(mm(pad.GetSize().x)-4.5)<1e-6 and pad.GetNetname()=='/GND'
solid_hits=[r for r in solid_hits if r!='HS80']
assert not solid_hits,solid_hits
# Screen unrelated top copper against the actual fin/web envelopes. Anchors
# are the intentional plated mounting contacts; all other pads are excluded.
copper_hits=[]
for x,y,w,h in solids:
    shape=p.SHAPE_RECT(p.VECTOR2I(p.FromMM(x),p.FromMM(y)),p.FromMM(w),p.FromMM(h))
    for item in list(b.GetTracks())+[a for f in b.GetFootprints() if f.GetReference()!='HS80' for a in f.Pads()]:
        if item.IsOnLayer(p.F_Cu) and item.GetEffectiveShape(p.F_Cu).Collide(shape,p.FromMM(.199)):
            copper_hits.append(item.m_Uuid.AsString())
    for zone in b.Zones():
        if not zone.GetIsRuleArea() and zone.IsOnLayer(p.F_Cu) and zone.GetFilledPolysList(p.F_Cu).Collide(shape,p.FromMM(.199)):
            copper_hits.append(zone.m_Uuid.AsString())
assert not copper_hits,copper_hits
result = {
    'status':'PASS_IMPLEMENTED_DRAWING_BASED_MOUNTING',
    'pcb_sha256':hashlib.sha256(board_file.read_bytes()).hexdigest(),
    'library_footprint':'Lab4_Mechanical:Boyd_6396BG_StraightPins',
    'library_footprint_check':'PASS: two pads, 25.4 mm pitch, 2.89 mm drills, 4.5 mm pads, one closed courtyard',
    'library_footprint_installed_in_active_board':True,
    'coordinate_system':'KiCad absolute mm; subtract (40,40) for board-relative coordinates',
    'part':'6396BG straight pins; NOT 6396B-P2G',
    'body_mm':[41.91,25.4,25.4], 'pin_centers_mm':pins,
    'recommended_finished_pth_diameter_mm':2.89,
    'study_pad_diameter_mm':4.5, 'device_mount_hole_diameter_mm':3.81,
    'device_screw_center_height_above_sink_bottom_mm':19.05,
    'mounting_face_y_mm':face_y, 'outer_envelope_mm':rect,
    'conservative_fin_web_blocks_mm':solids, 'block_clearance_mm':.5,
    'outer_envelope_courtyard_intersections':outer_hits,
    'fin_web_clearance_screen_intersections':solid_hits,
    'unrelated_top_copper_in_metal_envelopes':copper_hits,
    'nominal_uninsulated_flush_mount': {
        'pcb_thickness_mm':1.6,
        'st_short_lead_hole_to_tip_min_mm':21.9,
        'st_short_lead_hole_to_tip_max_mm':22.5,
        'short_lead_below_board_min_mm':round(21.9-19.05-1.6,3),
        'short_lead_below_board_max_mm':round(22.5-19.05-1.6,3),
        'other_row_hole_to_tip_min_mm':21.7,
        'minimum_either_row_below_board_mm':round(21.7-19.05-1.6,3),
        'bend_plane_above_board_min_mm':round(19.05-18.1,3),
        'bend_plane_above_board_max_mm':round(19.05-17.65,3),
        'package_bottom_above_board_min_mm':round(19.05-(17.75-2.65),3),
        'package_bottom_above_board_max_mm':round(19.05-(17.25-2.9),3),
    },
    'limits':[
        'Drawing-based placement and copper checks pass; no physical fit or thermal test is claimed.',
        'A fin-block/courtyard intersection is a clearance-screen finding, not measured physical interference.',
        'No credit for mounting components under the heatsink or between individual fins.',
        'No thermal qualification or complete supplier tolerance stack.',
        'Native DRC independently checks plated-anchor clearance on all copper layers; this script screens top metal contact.',
        'Soldered anchor pads are mechanical. Do not depend on the anodized body as insulation or as a reliable ground connection.',
    ],
}
(ROOT/'Heatsink-mounting-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

# A standalone dimensioned study; not a replacement for the active board.
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1300 740">',
     '<rect width="1300" height="740" fill="white"/>',
     '<g font-family="Arial,sans-serif" fill="#172b3a">',
     '<text x="30" y="34" font-size="23">6396BG / L298N — drawing-based mounting study</text>',
     '<text x="30" y="59" font-size="15">Implemented top view. Coordinates and dimensions in mm; physical assembly untested.</text>']
scale=11
def xy(x,y):return 50+(x-40)*scale,100+(y-40)*scale
def rectangle(a,fill,stroke,opacity=1):
    x,y=xy(a[0],a[1]);w,h=a[2]*scale,a[3]*scale
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" opacity="{opacity}"/>')
for r,v in boxes.items():
    if v[0]<100 and v[1]+v[3]<90 and v[0]+v[2]>40 and v[1]+v[3]>40:
        rectangle(v,'#ffe6de' if r in solid_hits else '#f1f5f9','#9aa9b5')
        x,y=xy(v[0]+v[2]/2,v[1]+v[3]/2)
        svg.append(f'<text x="{x}" y="{y}" font-size="11" text-anchor="middle">{html.escape(r)}</text>')
rectangle(rect,'none','#d48a00')
for s in solids:rectangle(s,'#34495e','#172b3a',.32)
for x,y in pins:
    a,c=xy(x,y)
    svg.append(f'<circle cx="{a}" cy="{c}" r="{2.25*scale}" fill="none" stroke="#007c91" stroke-width="2"/>')
    svg.append(f'<circle cx="{a}" cy="{c}" r="{2.89/2*scale}" fill="white" stroke="#007c91"/>')
labels=[
    'Mounting plan from manufacturer drawings',
    'Two soldered anchor pins: 25.40 mm pitch',
    'Recommended finished plated holes: 2.89 mm',
    'Sink: 41.91 wide x 25.40 deep x 25.40 high',
    'One M3 screw + nut through the device tab',
    'Sink screw center: 19.05 mm above base',
    '',
    'Green circles: proposed anchor pads/holes',
    'Dark blocks: conservative fin/web occupied space',
    'Orange outline: outer bounding rectangle',
    'Red parts: clearance-screen intersections',
    '',
    'Placement and local routing implemented.',
    'No unrelated courtyard in fin/web +0.5mm.',
    'No unrelated copper under top metal.',
    'U80/tab overlap is an explicit paired exception.',
    '',
    'Flush mount / 1.6 mm PCB height screen:',
    'Minimum lead projection, either row: 1.05 mm',
    'Lead bend above PCB: 0.95–1.40 mm',
    'Package bottom above PCB: 3.95–4.70 mm',
    'These are calculations, not physical fit tests.',
]
for i,line in enumerate(labels):svg.append(f'<text x="850" y="{100+i*24}" font-size="14">{html.escape(line)}</text>')
svg.append('</g></svg>')
(ROOT/'Heatsink-mounting-study.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ['status','pin_centers_mm','fin_web_clearance_screen_intersections','unrelated_top_copper_in_metal_envelopes','nominal_uninsulated_flush_mount']},indent=2))
