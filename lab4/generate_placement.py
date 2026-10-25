"""Create the initial, unrouted KiCad placement study from an exported netlist.

Run with KiCad's bundled Python (pcbnew). This is an engineering generation
tool, not a hardware setup script. Existing boards are protected by default.
After hand editing Lab4.kicad_pcb, export to another filename for comparison.
"""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('netlist', type=Path)
parser.add_argument('--footprints', type=Path, required=True)
parser.add_argument('--output', type=Path, default=ROOT/'KiCad/Lab4.kicad_pcb')
parser.add_argument('--replace', action='store_true')
args = parser.parse_args()
if args.output.exists() and not args.replace:
    parser.error('Board exists: use another --output or explicitly --replace.')
# pcbnew.SaveBoard can initialize default project rules. Preserve the existing
# project rather than silently replacing the team's manufacturing constraints.
project_file=args.output.with_suffix('.kicad_pro')
project_before=project_file.read_bytes() if project_file.exists() else None
tree = ET.parse(args.netlist).getroot()
b = p.BOARD()
b.SetCopperLayerCount(2)
b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
ORIGIN = (40, 40)
W, H = 120, 234
def vec(x,y):
    return p.VECTOR2I(p.FromMM(x+ORIGIN[0]),p.FromMM(y+ORIGIN[1]))
def mm(v): return p.ToMM(v)
def line(x1,y1,x2,y2,layer=p.Dwgs_User,width=.15):
    s=p.PCB_SHAPE(b);s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(vec(x1,y1));s.SetEnd(vec(x2,y2));s.SetLayer(layer);s.SetWidth(p.FromMM(width));b.Add(s)
def rect(x,y,w,h,layer=p.Dwgs_User):
    for a,c in [((x,y),(x+w,y)),((x+w,y),(x+w,y+h)),((x+w,y+h),(x,y+h)),((x,y+h),(x,y))]: line(*a,*c,layer)
def label(s,x,y,size=1,layer=p.Dwgs_User):
    t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(vec(x,y));t.SetLayer(layer);t.SetTextSize(p.VECTOR2I(p.FromMM(size),p.FromMM(size)));t.SetTextThickness(p.FromMM(.15));b.Add(t)
rect(0,0,W,H,p.Edge_Cuts)
label('PLACEMENT STUDY - UNROUTED - NOT FOR FABRICATION',60,-7,1.5)
label('120 x 234 mm proposal / chassis hole centers from team measurements',60,-3,1)
label('REAR / MOTOR END',60,2,1)
label('FRONT / STEERING END',60,232,1)

netmap={}; pinmap={}
for n in tree.findall('nets/net'):
    name=n.attrib['name']
    if name.startswith('unconnected-'): name=name.replace('/','{slash}')
    net=p.NETINFO_ITEM(b,name,int(n.attrib['code']));b.Add(net);netmap[name]=net
    for node in n.findall('node'): pinmap[(node.attrib['ref'],node.attrib['pin'])]=net
comps={c.attrib['ref']:c for c in tree.findall('components/comp')}
fps={}; missing=[]; positions={}
def load_fp(name):
    lib,part=name.split(':',1)
    directory=ROOT/'KiCad'/(lib+'.pretty') if lib.startswith('Lab4_') else args.footprints/(lib+'.pretty')
    fp=p.FootprintLoad(str(directory),part)
    if fp is None: raise ValueError('Missing footprint '+name)
    fp.SetFPID(p.LIB_ID(lib,part));return fp
for ref,c in comps.items():
    name=c.findtext('footprint','')
    if not name: missing.append(ref);continue
    fp=load_fp(name);fp.SetReference(ref);fp.SetValue(c.findtext('value',''))
    path=p.KIID_PATH()
    for uid in (c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps')).split('/'):
        if uid: path.push_back(p.KIID(uid))
    fp.SetPath(path)
    fp.SetSheetname(c.find('sheetpath').attrib['names'])
    for prop in c.findall('property'):
        if prop.attrib['name']=='Sheetfile': fp.SetSheetfile(prop.attrib['value'])
    for field in c.findall('fields/field'):
        if field.attrib['name'] not in ['Footprint','Datasheet','Description']:
            fp.SetField(field.attrib['name'],field.text or '')
            fp.GetField(field.attrib['name']).SetVisible(False)
    fp.SetField('Datasheet',c.findtext('datasheet',''))
    fp.GetField('Datasheet').SetVisible(False)
    for pad in fp.Pads():
        if (ref,pad.GetNumber()) in pinmap: pad.SetNet(pinmap[(ref,pad.GetNumber())])
    fp.Reference().SetLayer(p.F_Fab)
    fp.Reference().SetTextSize(p.VECTOR2I(p.FromMM(1),p.FromMM(1)))
    fp.Reference().SetTextThickness(p.FromMM(.12))
    fp.Value().SetVisible(False)
    b.Add(fp);fps[ref]=fp

def place(ref,x,y,angle=0):
    """Place footprint by its non-text bounding-box center (not pad-one anchor)."""
    fp=fps[ref];fp.SetOrientationDegrees(angle)
    bb=fp.GetBoundingBox(False,False);center=bb.GetCenter()
    fp.Move(vec(x,y)-center)
    positions[ref]=(x,y,angle)

# Repeated CAN cells: controller, local crystal and bypass, transceiver,
# and uncovered isolation/test headers. Bus A and B occupy separate columns.
def can_cell(n,x,y,term=True):
    k=n*10
    place(f'U{n}',x-4,y)
    place(f'U{n+1}',x+6,y)
    # Native origins match the locally routed revision. Keep the crystal near
    # OSC1/OSC2 and put the transceiver bypass in the gap between the two ICs.
    for ref,dx,dy,angle in [(f'Y{n}',-10,3,0),(f'C{k}',-13.3,4.8,270),
            (f'C{k+1}',-9.7,-.2,0),(f'R{k}',-2.9,-6.8,0),
            (f'C{k+2}',.4,-6.8,0),(f'R{k+1}',.9,5.2,0),
            (f'C{k+3}',.7,-4.5,0),(f'C{k+4}',1.05,.9,270)]:
        fps[ref].SetOrientationDegrees(angle)
        fps[ref].SetPosition(vec(x+dx,y+dy));positions[ref]=(x+dx,y+dy,angle)
    place(f'J{n}',x-7,y-13)
    place(f'J{n+1}',x+5,y-13,90)
    if term:
        place(f'JP{n}',x+6,y+7,90);place(f'R{k+2}',x+6,y+3.5)
    label(f'{"FRONT" if n<20 else "REAR" if n<30 else "PI"} CAN {"A" if n%10==0 else "B"}',x,y+11,.9)
for n,x,y in [(20,78,44),(24,105,44),(30,65,115),(34,99,115),(10,78,169),(14,105,169)]:
    can_cell(n,x,y,n<30)

def mcu(n,x,y):
    base=n*10
    place(f'U{n}',x,y)
    # Supply capacitors follow their associated package sides.
    cs=[(-3,8),(6,8),(8,-4),(-4,-8),(-8,-4),(-11,-1),(1,8),(-8,3),(-11,3),(-8,-1),(10,8)]
    for i,(dx,dy) in enumerate(cs): place(f'C{base+i}',x+dx,y+dy,90 if abs(dx)>abs(dy) else 0)
    place(f'FB{n}',x-11,y+6)
    for i,(dx,dy) in enumerate([(7,-8),(-11,-4),(10,5)]):place(f'R{base+i}',x+dx,y+dy)
    for i in range(4):
        place(f'D{base+10+i}',x-12+6*i,y-13)
        place(f'R{base+10+i}',x-12+6*i,y-16)
    place(f'J{base}',x+12,y-8.5)
    place(f'J{base+1}',x-15,y,0)
    place(f'J{base+2}',x+14,y,0)
    for i in range(1 if n==50 else 6): place(f'R{base+30+i}',x-10+i*3.8,y+12)
    label(f'{"FRONT" if n==50 else "REAR"} STM32',x,y+16,1)
mcu(60,31,64)
mcu(50,31,163)
for ref,x,y,ang in [('J603',4,61,0),('J604',54,61,0),('J605',61,66,0),
                     ('J503',4,163,0),('J504',54,158,0),('J505',61,153,0),
                     ('J703',4,104,0),('J704',10,131,0)]:place(ref,x,y,ang)

# Standard Pi viewed from above: USB/Ethernet right, GPIO along its rear edge.
# The female socket is assembled on our PCB UNDERSIDE. Physical Pi pin 1 is
# the inner row at (8.37,4.77), and pin 2 is the outer row at (8.37,2.23).
# Pin mapping is checked independently after saving; no row swaps are assumed.
PI_X, PI_Y = 30, 89
fp=fps['J70'];fp.Flip(fp.GetPosition(),p.FLIP_DIRECTION_LEFT_RIGHT)
fp.SetOrientationDegrees(270);fp.SetPosition(vec(PI_X+8.37,PI_Y+4.77))
positions['J70']=(PI_X+32.5,PI_Y+3.5,270)
label('J70 SOCKET ON UNDERSIDE / PIN 1',PI_X+32.5,PI_Y-3,.8)
label('1',PI_X+8.37,PI_Y+8,.85,p.F_SilkS)
label('2',PI_X+8.37,PI_Y-1,.85,p.F_SilkS)

# Two motor-current channels are beside the motor-stage reservation.
for u,x in [(2,19),(3,44)]:
    cb=3 if u==2 else 6;rb=3 if u==2 else 6
    place(f'U{u}',x,38)
    for i,(dx,dy) in enumerate([(6,-3),(6,0),(9,3)]):place(f'C{cb+i}',x+dx,38+dy,90)
    for i,(dx,dy) in enumerate([(9,-3),(9,0),(6,3)]):place(f'R{rb+i}',x+dx,38+dy,90)
    place(f'J{u}',x,45,90)
# Servo sensing / front output area.
for ref,x,y,ang in [('R1',27,185,0),('U1',39,185,0),('C1',39,181,0),('R2',44,183,90),('C2',44,187,90),('J1',51,185,90)]:place(ref,x,y,ang)

# Power input remains a schematic placeholder; the mechanical reservation is larger.
for ref,x,y,ang in [('J40',74,7,0),('F1',88,17,90),('Q1',109,17,0),('R400',109,25,0),('R401',113,25,0),('D40',104,25,0),('C400',64,21,0),('J41',76,23,90)]:place(ref,x,y,ang)
for k,x in enumerate([22,60,98]):
    base=410+k*10;y=204
    # TI TPS564252 Fig. 8-26: SW faces the inductor; FB stays on the
    # opposite side. Actual loop copper, Kelvin ground and vias remain unrouted.
    place(f'U{40+k}',x-4,y,180)
    place(f'L{k+1}',x+2.5,y)
    for i,dx,dy,angle in [(0,-3.8,6.5,180),(1,-3.8,2.4,180),(2,9,-2.2,90),(3,9,1.8,270),(4,-7.8,-.5,0)]: place(f'C{base+i}',x+dx,y+dy,angle)
    for i,dx,dy,angle in [(0,-7.8,1.5,0),(1,-7.8,3.5,180),(2,-6,-6.5,90),(3,-3,-5,90),(4,-8,-4,0)]:place(f'R{base+i}',x+dx,y+dy,angle)
    place(f'J{42+k}',x+13.5,y,0)
    label(['6.6 V SERVO','5.1 V PI','3.3 V LOGIC'][k],x,194,.9)
for ref,x,y in [('C700',19,85),('C701',21,80),('R700',6,140),('C702',20,145)]:place(ref,x,y)
for i in range(4):
    place(f'D{710+i}',35+7*i,85);place(f'R{710+i}',35+7*i,81)

# Actuator connections added 23 October. All coordinates remain a placement study.
for ref,x,y,ang in [('U80',32,23,0),('C800',48,25,0),('C801',48,28,0),('C802',55,7,0),
    ('J80',24,7,0),('J81',40,7,0),('J82',15,98,0),('J83',66,77,0),('U81',99,62,0),('C803',106,62,0),
    ('J90',107,222,0),('R540',56,189,0)]:place(ref,x,y,ang)
for i in range(8):place(f'D{800+i}',8 if i<4 else 60,(16 if i<4 else 32)+(i%4)*6,0)
for i in range(4):
    place(f'R{800+i}',75+i*5,65,90)
    place(f'R{804+i}',75+i*5,61,90)
for base,y in [(550,186),(650,76)]:
    for i,x in enumerate([76,96] if base==550 else [81,104]):
        place(f'Q{base+i}',x,y)
        place(f'R{base+i}',x-5,y-2,90)
        place(f'R{base+10+i}',x-5,y+2,90)
        place(f'R{base+20+i}',x+5,y-2,90)
        place(f'J{base+i}',x+9,y+2)
# Verified GCT A1 land pattern; physical terminal pairs are mapped to two contacts.
for ref,x,y in [('SW60',12,81),('SW61',27,85),('SW50',12,185),('SW51',60,179),('SW70',12,144)]:
    # Use the body/pad-pattern origin; the pin marker makes the drawn bbox asymmetric.
    fps[ref].SetPosition(vec(x,y));positions[ref]=(x,y,0)
assert set(positions)==set(fps),('Unplaced:',set(fps)-set(positions))

reservations=[]
def reserve(name,x,y,w,h,kind='missing',exclude_footprints=True,layer=p.F_Cu,copper=False):
    reservations.append(dict(name=name,x=x,y=y,w=w,h=h,kind=kind,layer=p.LayerName(layer)))
    rect(x,y,w,h);label(name,x+w/2,y+h/2,.85)
    if exclude_footprints:
        z=p.ZONE(b);z.SetLayer(layer);z.SetIsRuleArea(True)
        z.SetDoNotAllowFootprints(True);z.SetDoNotAllowTracks(copper);z.SetDoNotAllowVias(copper);z.SetDoNotAllowPads(copper);z.SetDoNotAllowZoneFills(copper)
        poly=z.Outline();poly.NewOutline()
        for xx,yy in [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]:v=vec(xx,yy);poly.Append(v.x,v.y)
        b.Add(z)
reserve('6396BG 41.91x25.4 ENVELOPE / MOUNT TO VERIFY',11.045,10.3,41.91,25.4,exclude_footprints=False)
reserve('INPUT CONNECTOR ENVELOPE',66,5,12,12,exclude_footprints=False)

reserve('Pi 4 BELOW PCB / TOP COMPONENTS ALLOWED',PI_X,PI_Y,85,56,'pi',False)
# Bottom-only placement restrictions leave the top available. Split around the
# socket and mounting supports. Through-hole tails need a separate Z check.
reserve('Pi BOTTOM BODY CLEARANCE',38,97,49,39,'clearance',layer=p.B_Cu)
reserve('Pi BOTTOM PORT CLEARANCE',97,89,23,56,'clearance',layer=p.B_Cu)
reserve('Pi USB / ETHERNET EXIT BELOW BOARD',115,89,5,56,'cable',layer=p.B_Cu)
reserve('Pi microSD ACCESS BELOW BOARD',0,109,30,16,'cable',layer=p.B_Cu)
# Preliminary antenna review envelope, not a manufacturer RF guarantee. Avoid
# copper and components on both layers; still verify Wi-Fi with the metal car.
for layer in [p.F_Cu,p.B_Cu]:
    reserve('Pi ANTENNA REVIEW / NO COPPER',26,98,18,12,'rf',layer=layer,copper=True)

def mount(ref,x,y,diam,kind):
    fp=load_fp('Lab4_Mechanical:Pi_support_M2.5_D5.5' if diam==2.7 else 'MountingHole:MountingHole_3.2mm_M3')
    fp.SetReference(ref);fp.SetValue(kind);fp.SetPosition(vec(x,y));fp.SetBoardOnly(True);fp.Value().SetVisible(False);b.Add(fp);fps[ref]=fp;positions[ref]=(x,y,0)
    # Chassis: 3 mm from hole edge. Pi: 3 mm from center, accommodating <=5.5 mm
    # hardware plus margin, because the standard Pi GPIO connector is close.
    # This distinction is recorded as a course-clearance review item.
    r=3 if diam==2.7 else diam/2+3
    rect(x-r,y-r,2*r,2*r)
    # Reserve copper for the screw/spacer on both sides. The empty NPTH pad is
    # permitted; electrical footprint clearance is checked separately.
    for layer in [p.F_Cu,p.B_Cu]:
        z=p.ZONE(b);z.SetLayer(layer);z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
        poly=z.Outline();poly.NewOutline()
        # Circumscribed polygon keeps the minimum clearance at least r.
        rr=r/math.cos(math.pi/48)
        for k in range(48):
            a=2*math.pi*k/48;v=vec(x+rr*math.cos(a),y+rr*math.sin(a));poly.Append(v.x,v.y)
        b.Add(z)
    label(ref+(' TARGET' if kind=='UNMEASURED chassis target' else ''),x,y-r-1,.8)
for i,(x,y) in enumerate([(7.5,7),(112.5,7),(35,227),(85,227)],1):mount('H'+str(i),x,y,3.2,'Measured chassis center; M3 PCB drill proposed')
for i,(x,y) in enumerate([(33.5,92.5),(91.5,92.5),(33.5,141.5),(91.5,141.5)],5):mount('H'+str(i),x,y,2.7,'Pi support <=5.5mm hardware OD')

# Mechanical quantities must not be confused with the schematic BOM.
b.SetFileName(str(args.output));b.BuildConnectivity();p.SaveBoard(str(args.output),b)
if project_before is not None: project_file.write_bytes(project_before)

def bounds(fp):
    fp.BuildCourtyardCaches();bb=fp.GetCourtyard(p.B_CrtYd if fp.IsFlipped() else p.F_CrtYd).BBox()
    if bb.GetWidth()==0:bb=fp.GetBoundingBox(False,False)
    return [mm(bb.GetX())-40,mm(bb.GetY())-40,mm(bb.GetWidth()),mm(bb.GetHeight())]
records=[]
for ref,fp in fps.items():
    records.append(dict(reference=ref,value=fp.GetValue(),footprint=str(fp.GetFPID().GetLibNickname())+':'+str(fp.GetFPID().GetLibItemName()),
        x_mm=round(mm(fp.GetPosition().x)-40,4),y_mm=round(mm(fp.GetPosition().y)-40,4),
        rotation_deg=fp.GetOrientationDegrees(),layer=fp.GetLayerName(),bbox=bounds(fp),schematic=ref in comps))
with (ROOT/'Placement-coordinates.csv').open('w',newline='',encoding='utf-8') as f:
    keys=['reference','value','footprint','x_mm','y_mm','rotation_deg','layer','schematic'];w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(records)
pi=dict(x_mm=PI_X,y_mm=PI_Y,width_mm=85,height_mm=56,orientation='component side up, below main PCB',
        board_gap_mm=22,main_pcb_chassis_gap_mm=35,pi_thickness_assumed_mm=1.6,
        socket='Samtec ESQ-120-44-L-D',socket_body_height_mm=18.67,
        gpio_tip_height_mm=8.5,usb_height_mm=16.4,header_insertion_min_mm=3.68,header_insertion_max_mm=6.35,
        support_max_od_mm=5.5,provisional=True)
(ROOT/'placement-data.json').write_text(json.dumps(dict(width_mm=W,height_mm=H,pi=pi,components=records,reservations=reservations,missing_footprints=missing),indent=2),encoding='utf-8')
print(json.dumps(dict(board=str(args.output),schematic_footprints=len(comps)-len(missing),missing=missing,mechanical_holes=8,nets=len(netmap))))
