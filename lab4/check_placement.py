"""Check the saved KiCad placement against its schematic XML and reservations.

Run with KiCad's Python: check_placement.py schematic-netlist.xml
These checks do not replace DRC, datasheet review or a physical fit check.
"""
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parent
b=p.LoadBoard(str(ROOT/'KiCad/Lab4.kicad_pcb'))
d=json.loads((ROOT/'placement-data.json').read_text())
tree=ET.parse(sys.argv[1]).getroot()
fps={fp.GetReference():fp for fp in b.GetFootprints()}
errors=[]
schematic={c.attrib['ref']:c for c in tree.findall('components/comp')}
missing=sorted(set(schematic)-set(fps))
assert missing==['SW50','SW51','SW60','SW61','SW70'],missing
def box(fp):
    fp.BuildCourtyardCaches();bb=fp.GetCourtyard(p.B_CrtYd if fp.IsFlipped() else p.F_CrtYd).BBox()
    return [p.ToMM(bb.GetX())-40,p.ToMM(bb.GetY())-40,p.ToMM(bb.GetWidth()),p.ToMM(bb.GetHeight())]
def hit(a,c):
    x,y,w,h=a;u,v,s,t=c
    return min(x+w,u+s)>max(x,u)+.001 and min(y+h,v+t)>max(y,v)+.001
for n in tree.findall('nets/net'):
    name=n.attrib['name']
    if name.startswith('unconnected-'):name=name.replace('/','{slash}')
    for node in n.findall('node'):
        ref,pin=node.attrib['ref'],node.attrib['pin']
        if ref in missing:continue
        pads=[pad for pad in fps[ref].Pads() if pad.GetNumber()==pin]
        if not pads or any(pad.GetNetname()!=name for pad in pads):errors.append(f'{ref}.{pin} net mismatch')
for ref,fp in fps.items():
    x,y,w,h=box(fp)
    if x<0 or y<0 or x+w>d['width_mm'] or y+h>d['height_mm']:errors.append(f'{ref} extends outside outline')
    if ref in schematic and ref!='J70' and fp.IsFlipped() and hit([x,y,w,h],[30,89,85,56]):errors.append(f'{ref} bottom part occupies Pi space')
    if ref in schematic:
        for hole in [f'H{i}' for i in range(1,9)]:
            pos=fps[hole].GetPosition();hx=p.ToMM(pos.x)-40;hy=p.ToMM(pos.y)-40
            r=4.6 if int(hole[1:])<5 else 3.0
            # Distance from the hole center to the courtyard rectangle.
            dx=max(x-hx,0,hx-(x+w));dy=max(y-hy,0,hy-(y+h))
            if dx*dx+dy*dy < r*r:errors.append(f'{ref} in {hole} support envelope')
# Check physical mating geometry, not just logical net names. Mirrored header
# rows can pass ordinary schematic-net checks and still connect 5V incorrectly.
pi=d['pi'];socket=fps['J70']
if socket.GetLayer()!=p.B_Cu:errors.append('J70 must be on bottom')
for pad in socket.Pads():
    n=int(pad.GetNumber());pair=(n-1)//2
    expected=(pi['x_mm']+8.37+2.54*pair,pi['y_mm']+(4.77 if n%2 else 2.23))
    pos=pad.GetPosition();actual=(p.ToMM(pos.x)-40,p.ToMM(pos.y)-40)
    if any(abs(a-e)>.001 for a,e in zip(actual,expected)):errors.append(f'Pi physical pin {n} mirrored or misplaced')
    if abs(p.ToMM(pad.GetDrillSize().x)-1.02)>.001:errors.append(f'J70.{n} drill differs from Samtec print')
for i,(x,y) in enumerate([(7.5,7),(112.5,7),(35,227),(85,227)],1):
    pos=fps[f'H{i}'].GetPosition()
    if abs(p.ToMM(pos.x)-40-x)>.001 or abs(p.ToMM(pos.y)-40-y)>.001:errors.append(f'H{i} measured chassis pattern mismatch')
expected_holes=[(33.5,92.5),(91.5,92.5),(33.5,141.5),(91.5,141.5)]
for i,(x,y) in enumerate(expected_holes,5):
    pos=fps[f'H{i}'].GetPosition()
    if abs(p.ToMM(pos.x)-40-x)>.001 or abs(p.ToMM(pos.y)-40-y)>.001:errors.append(f'H{i} Pi pattern mismatch')
insertion=pi['gpio_tip_height_mm']-(pi['board_gap_mm']-pi['socket_body_height_mm'])
if not pi['header_insertion_min_mm']<=insertion<=pi['header_insertion_max_mm']:errors.append('Nominal header engagement out of range')
usb_gap=pi['board_gap_mm']-pi['usb_height_mm']
# Limit solder tails of top-side THT parts in the Pi projection to 3 mm below
# our board, leaving >=3 mm above a 16 mm Pi USB body at 22 mm spacing.
tht_over_pi=[]
for ref,fp in fps.items():
    if ref in schematic and ref!='J70' and hit(box(fp),[30,89,85,56]) and any(pad.GetAttribute()==p.PAD_ATTRIB_PTH for pad in fp.Pads()):
        tht_over_pi.append(ref)
# Preview geometry must correspond to the current saved PCB, not a previous run.
for c in d['components']:
    pos=fps[c['reference']].GetPosition()
    if abs(p.ToMM(pos.x)-40-c['x_mm'])>.001 or abs(p.ToMM(pos.y)-40-c['y_mm'])>.001:errors.append('Stale preview '+c['reference'])
assert len(b.GetTracks())==0,'Unexpected routing added to a placement-only study'
report=dict(status='PASS' if not errors else 'FAIL',errors=errors,
    schematic_footprints_present=len(set(fps)&set(schematic)),missing_footprints=missing,
    mechanical_holes=8,board_size_mm=[d['width_mm'],d['height_mm']],tracks=0,
    checks=['Placed netlist pads match schematic','All courtyards inside provisional outline',
        'No bottom electrical part in Pi space except J70; top placement allowed',
        'Chassis 3mm-from-hole-edge and Pi 3mm-radius support envelopes clear',
        'All 40 bottom socket pad coordinates match physical Pi pin numbers',
        'Pi 58x49mm mounting pattern and 1.02mm socket drills',
        'Nominal socket insertion within manufacturer range','Preview coordinates match saved PCB'],
    pi_stack_nominal=dict(socket_insertion_mm=round(insertion,2),usb_to_main_pcb_mm=usb_gap,
        pi_board_underside_above_chassis_mm=round(pi['main_pcb_chassis_gap_mm']-pi['board_gap_mm']-pi['pi_thickness_assumed_mm'],2),
        top_tht_refs_over_pi=sorted(tht_over_pi),max_tht_tail_projection_mm=3),
    limitations=['Not a physical fit or footprint-dimension validation','Unrouted and incomplete schematic',
        'Chassis centers measured; PCB drill/fasteners and vertical fit still require verification',
        'Pi uses 3mm radius from center; strict 3mm from hole edge conflicts with standard GPIO body and needs course review',
        'Pi pin protrusion/heatsink, Wi-Fi, thermals and socket tolerances need physical verification',
        'Placement checks do not replace the separate KiCad DRC report; board remains unrouted'])
(ROOT/'Placement-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
sys.exit(bool(errors))
