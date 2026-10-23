"""Render a placement overview and a true-size paper fit template from PCB data.

Chassis hole centers use team caliper dimensions. Board outline and stack remain proposed.
Requires reportlab and Pillow. No photograph is altered or used as a ruler.
"""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parent
d=json.loads((ROOT/'placement-data.json').read_text())
colors={'missing':'#fff0d2','switch':'#fff0d2','pi':'#e2efff','clearance':'#e2efff','cable':'#ebf3fb','rf':'#fce4df'}
img=Image.new('RGB',(1440,1740),'#f5f7fa');dr=ImageDraw.Draw(img)
fontdir=Path('C:/Windows/Fonts')
def ft(s,bold=False):return ImageFont.truetype(str(fontdir/('arialbd.ttf' if bold else 'arial.ttf')),s)
S=6;OX=75;OY=180
def xy(x,y):return OX+S*x,OY+S*y
def rbox(x,y,w,h):return (*xy(x,y),*xy(x+w,y+h))
dr.text((75,35),'Lab 4 | Direct Pi connection',font=ft(38,True),fill='#16354e')
dr.text((75,89),'120 x 234 mm proposal  /  279 electrical footprints placed',font=ft(23),fill='#334b60')
dr.text((75,125),'UNROUTED - measured chassis hole centers - NOT FOR FABRICATION',font=ft(22,True),fill='#9b4800')
dr.rectangle(rbox(0,0,120,234),fill='white',outline='#16354e',width=3)
for r in d['reservations']:
    if r['kind']=='clearance':continue
    dr.rectangle(rbox(r['x'],r['y'],r['w'],r['h']),fill=colors[r['kind']],outline='#b17820' if r['kind'] in ['missing','switch'] else '#7392b6',width=2)
for c in d['components']:
    x,y,w,h=c['bbox'];ref=c['reference']
    if not c['schematic']:
        rad=(2.7 if int(ref[1:])>=5 else 3.2)/2
        cx,cy=c['x_mm'],c['y_mm'];dr.ellipse(rbox(cx-rad,cy-rad,2*rad,2*rad),fill='white',outline='#9b4800' if int(ref[1:])<5 else '#315d9b',width=2)
        dr.text(xy(cx-3,cy-6),ref,font=ft(13,True),fill='#173b53')
    else:
        color='#c77729' if c['layer']=='B.Cu' else '#214b69' if ref.startswith('U') else '#6592a7' if ref.startswith('J') else '#abbbc6'
        dr.rectangle(rbox(x,y,w,h),fill=color,outline='#244052',width=1)
        if ref.startswith(('U','J','L','F','Q')):dr.text(xy(x,y+h+.2),ref,font=ft(11),fill='#173b53')
def onboard(lines,x,y):
    for i,line in enumerate(lines):dr.text(xy(x,y+i*3.1),line,font=ft(16,True),fill='#244052')

onboard(['Pi BELOW this area','Top CAN circuits shown'],46,134)

dr.text(xy(42,235),'FRONT / STEERING',font=ft(17,True),fill='#16354e')
dr.text(xy(38,-5),'REAR / DRIVE MOTORS',font=ft(17,True),fill='#16354e')
side=[('What this establishes',[
    'Actual footprint sizes and initial locations.',
    'Pi underneath; top-side parts overlap it.',
    'A board-size proposal to check on the car.']),
    ('Mounting proposals',[
    'H1-H4: measured chassis centers.',
    'Rear 105 mm / front 50 mm spacing.',
    'H5-H8: Pi mounting pattern, 58 x 49 mm.',
    'Rows 220 mm apart; centers aligned.']),
    ('Planned electrical connections',[
    'Every placed pad retains its schematic net.',
    'No copper tracks or ground planes yet.',
    'J70: bottom-mounted 40-pin socket.',
    'No GPIO cable. Pin geometry checked.']),
    ('Still required before routing',[
    'Five verified switch footprints.',
    'Resolve motor current limit and heat.',
    '1 oz copper; 0.15 mm buck-pad exception.',
    'Check battery holder, heatsink and cables.',
    'Confirm screws and vertical stack fit.']),
    ('Placement key',[
    'Blue block: Pi mounted BELOW this area.',
    'Orange connector: socket on underside.',
    'Pink: preliminary antenna review area.',
    'Amber block: future circuit/switch space.',
    'Dark outlines: real component footprints.',
    'Battery pack mounts separately; no holder',
    'fit is claimed on this PCB.'])]
y=190
for title,lines in side:
    dr.text((860,y),title,font=ft(25,True),fill='#16354e');y+=43
    for line in lines:dr.text((860,y),line,font=ft(20),fill='#334b60');y+=30
    y+=38
dr.text((75,1626),'Geometry proposal only. Board width over the tapered front plate and wheel/linkage clearance need a physical fit check.',font=ft(20),fill='#334b60')
dr.text((75,1660),'Source: KiCad placement coordinates. The schematic is still incomplete; a successful placement is not a fabrication approval.',font=ft(20),fill='#334b60')
img.save(ROOT/'Placement-overview.png')

pdf=canvas.Canvas(str(ROOT/'Placement-fit-template.pdf'),pagesize=(210*mm,297*mm))
pdf.setTitle('Lab 4 - 1:1 PCB fit template - provisional')
pdf.setFont('Helvetica-Bold',14);pdf.drawString(15*mm,282*mm,'Lab 4 - provisional PCB fit template')
pdf.setFont('Helvetica',9);pdf.drawString(15*mm,276*mm,'Print at 100% / Actual size. Check the 50 mm bar before comparing with the car.')
pdf.setFont('Helvetica-Bold',9);pdf.drawString(15*mm,270*mm,'MEASURED HOLE CENTERS - UNROUTED - NOT FOR FABRICATION')
BX=45;BY=26
def p_rect(x,y,w,h,fill=None,stroke='#577386'):
    pdf.setStrokeColor(HexColor(stroke));pdf.setLineWidth(.15*mm)
    if fill:pdf.setFillColor(HexColor(fill))
    pdf.rect((BX+x)*mm,(BY+234-y-h)*mm,w*mm,h*mm,fill=int(fill is not None),stroke=1)
p_rect(0,0,120,234,None,'#000000')
pdf.setFillColor(HexColor('#000000'));pdf.setFont('Helvetica-Bold',8)
pdf.drawString(45*mm,263*mm,'REAR / DRIVE MOTORS     (0,0) at upper-left; x right, y down')
pdf.drawCentredString(105*mm,23*mm,'FRONT / STEERING WHEELS')
for r in d['reservations']:
    if r['kind']!='clearance':p_rect(r['x'],r['y'],r['w'],r['h'],colors[r['kind']])
for c in d['components']:
    ref=c['reference']
    if c['schematic']:
        p_rect(*c['bbox'],None,'#648293')
    else:
        cx=(BX+c['x_mm'])*mm;cy=(BY+234-c['y_mm'])*mm
        pdf.setStrokeColor(HexColor('#000000'));pdf.setLineWidth(.2*mm)
        pdf.circle(cx,cy,(1.35 if int(ref[1:])>=5 else 1.6)*mm)
        pdf.line(cx-2.5*mm,cy,cx+2.5*mm,cy);pdf.line(cx,cy-2.5*mm,cx,cy+2.5*mm)
        pdf.setFillColor(HexColor('#000000'));pdf.setFont('Helvetica-Bold',7)
        pdf.drawString(cx+2*mm,cy+2*mm,ref)
pdf.setFillColor(HexColor('#183b55'));pdf.setFont('Helvetica-Bold',10)
pdf.setFont('Helvetica',7);pdf.drawCentredString(115*mm,123*mm,'Pi BELOW PCB / H5-H8 supports')
pdf.setFillColor(HexColor('#000000'));pdf.setFont('Helvetica',8)
pdf.drawString(15*mm,20*mm,'H1-H4: measured centers; M3 PCB drills proposed. Chassis holes measured 4.5 mm.')
pdf.drawString(15*mm,15*mm,'Check wires, steering travel, Pi below the PCB, port access and separate battery location.')
pdf.setLineWidth(.4*mm);pdf.line(15*mm,8*mm,65*mm,8*mm)
pdf.line(15*mm,6*mm,15*mm,10*mm);pdf.line(65*mm,6*mm,65*mm,10*mm)
pdf.drawString(70*mm,7*mm,'This bar must measure 50 mm.')

# Dimensioned schematic section, separate from the true-size top-view template.
sideimg=Image.new('RGB',(1500,900),'#f5f7fa');sd=ImageDraw.Draw(sideimg)
sd.text((65,35),'How the boards stack - proposed dimensions',font=ft(36,True),fill='#16354e')
sd.text((65,90),'Pi component side faces UP. J70 socket is soldered to the UNDERSIDE of our PCB.',font=ft(23),fill='#334b60')
# Drawing is schematic, not a manufacturing scale drawing.
sd.rectangle((160,700,1080,723),fill='#676f78')
sd.rectangle((160,260,1080,280),fill='#1d7472')
sd.rectangle((350,550,970,571),fill='#46794b')
for x in [205,1015]:
    sd.rectangle((x,280,x+24,700),fill='#bf9d59')
for x in [380,910]:
    sd.rectangle((x,280,x+18,550),fill='#c9b47e')
sd.rectangle((475,280,540,510),fill='#263441')
for x in [489,505,521]:sd.rectangle((x,482,x+4,550),fill='#d2a94c')
sd.rectangle((735,356,850,550),fill='#b6bec7',outline='#5b6570',width=2)
sd.rectangle((590,520,640,550),fill='#333333')
sd.rectangle((600,225,650,260),fill='#333333')
sd.rectangle((815,217,845,260),fill='#777777')
sd.text((170,190),'Our PCB: parts / jumpers / probes on TOP',font=ft(25,True),fill='#16354e')
sd.text((350,585),'Pi PCB (1.6 mm assumed)',font=ft(23,True),fill='#315d36')
sd.text((160,745),'Existing metal chassis plate',font=ft(23,True),fill='#4a525b')
sd.text((550,325),'Tall socket',font=ft(22,True),fill='#263441')
sd.text((550,355),'18.67 mm body',font=ft(19),fill='#263441')
sd.text((730,395),'USB',font=ft(22,True),fill='#263441')
sd.text((728,425),'16 mm',font=ft(20),fill='#263441')
def dimension(x,y1,y2,label,small=None):
    sd.line((x,y1,x,y2),fill='#235271',width=2)
    for y in (y1,y2):sd.line((x-8,y,x+8,y),fill='#235271',width=2)
    sd.text((x+17,(y1+y2)/2-17),label,font=ft(24,True),fill='#16354e')
    if small:sd.text((x+17,(y1+y2)/2+16),small,font=ft(18),fill='#334b60')
dimension(1130,280,550,'22 mm','Pi-to-PCB gap')
dimension(1130,571,700,'11.4 mm','before underside parts')
sd.text((60,825),'35 mm chassis standoffs proposed. All heights and mating must be checked on the actual assembly.',font=ft(23),fill='#9b4800')
sideimg.save(ROOT/'Pi-stack-side-view.png')

pdf.showPage()
pdf.setFont('Helvetica-Bold',14);pdf.drawString(15*mm,282*mm,'Pi alignment and vertical fit check')
pdf.setFont('Helvetica',9);pdf.drawString(15*mm,275*mm,'Top view below is 1:1. Place the unpowered Pi component-side-up to compare holes and pins.')
PX=20;PY=202
pdf.setStrokeColor(HexColor('#16354e'));pdf.setFillColor(HexColor('#e2efff'))
pdf.roundRect(PX*mm,PY*mm,85*mm,56*mm,3*mm,stroke=1,fill=1)
for x,y in [(3.5,3.5),(61.5,3.5),(3.5,52.5),(61.5,52.5)]:
    pdf.circle((PX+x)*mm,(PY+56-y)*mm,1.35*mm,stroke=1,fill=0)
for i in range(1,41):
    x=8.37+2.54*((i-1)//2);y=4.77 if i%2 else 2.23
    pdf.circle((PX+x)*mm,(PY+56-y)*mm,.5*mm,stroke=1,fill=0)
pdf.setFillColor(HexColor('#16354e'))
pdf.setFont('Helvetica-Bold',8);pdf.drawString(31*mm,244*mm,'Pin 1: inner row, left end')
pdf.drawString(34*mm,220*mm,'Raspberry Pi 4: 85 x 56 mm')
pdf.drawString(34*mm,215*mm,'58 x 49 mm hole centers')
pdf.setFont('Helvetica',9)
for i,line in enumerate(['USB / Ethernet face right.', 'GPIO row faces the REAR.', 'microSD is on Pi underside.', 'Do not use this as a drill guide.', 'Main-PCB Pi origin: (30,89) mm.']):
    pdf.drawString(113*mm,(251-i*7)*mm,line)
pdf.drawImage(str(ROOT/'Pi-stack-side-view.png'),15*mm,83*mm,width=180*mm,height=108*mm)
pdf.setFont('Helvetica-Bold',10);pdf.drawString(15*mm,73*mm,'Record from the unpowered physical mock-up:')
pdf.setFont('Helvetica',9)
for i,line in enumerate(['Main-PCB underside above chassis: ______ mm (proposal 35 mm).',
    'Pi top to main-PCB underside: ______ mm (proposal 22 mm).',
    'Lowest Pi part / card / wire above metal: ______ mm.',
    'Tallest Pi feature, including cooler: ______ mm above Pi board.',
    'Compare H1-H4 with measured chassis holes; do not drill from this print.',
    'Can USB, Ethernet, microSD and cables be reached? __________________']):
    pdf.drawString(15*mm,(65-i*7)*mm,line)
pdf.setFont('Helvetica',7);pdf.drawString(15*mm,16*mm,'Pi mounting hardware OD <=5 mm proposed. Review the course 3 mm hole-clearance interpretation before fabrication.')
pdf.save()
print('Created direct-Pi placement overview, side view and two-page true-size fit template.')
