"""Render a placement overview and a true-size paper fit template from PCB data.

Chassis centers use the team-selected CAD pattern, checked against caliper dimensions.
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
img=Image.new('RGB',(1440,1860),'#f5f7fa');dr=ImageDraw.Draw(img)
fontdir=Path('C:/Windows/Fonts')
def ft(s,bold=False):return ImageFont.truetype(str(fontdir/('arialbd.ttf' if bold else 'arial.ttf')),s)
S=6;OX=75;OY=180
LEFT,TOP,RIGHT,BOTTOM=d['outline_bounds_mm']
def xy(x,y):return OX+S*(x-LEFT),OY+S*(y-TOP)
def rbox(x,y,w,h):return (*xy(x,y),*xy(x+w,y+h))
dr.text((75,35),'Lab 4 | Direct Pi connection',font=ft(38,True),fill='#16354e')
dr.text((75,89),f"{d['width_mm']:.0f} x {d['height_mm']:.3f} mm  /  {sum(c['schematic'] for c in d['components'])} electrical footprints placed",font=ft(23),fill='#334b60')
dr.text((75,125),'PLACEMENT PREVIEW - selected CAD hole centers - NOT FOR FABRICATION',font=ft(22,True),fill='#9b4800')
dr.rectangle(rbox(LEFT,TOP,d['width_mm'],d['height_mm']),fill='white',outline='#16354e',width=3)
for r in d['reservations']:
    if r['kind']=='clearance':continue
    dr.rectangle(rbox(r['x'],r['y'],r['w'],r['h']),fill=colors[r['kind']],outline='#b17820' if r['kind'] in ['missing','switch'] else '#7392b6',width=2)
for c in d['components']:
    x,y,w,h=c['bbox'];ref=c['reference']
    if not c['schematic'] and ref.startswith('H') and ref[1:].isdigit():
        rad=c['finished_drill_mm']/2
        cx,cy=c['x_mm'],c['y_mm'];dr.ellipse(rbox(cx-rad,cy-rad,2*rad,2*rad),fill='white',outline='#9b4800' if int(ref[1:])<5 else '#315d9b',width=2)
        dr.text(xy(cx-3,cy-6),ref,font=ft(13,True),fill='#173b53')
    else:
        color='#c77729' if c['layer']=='B.Cu' else '#214b69' if ref.startswith('U') else '#6592a7' if ref.startswith('J') else '#abbbc6'
        dr.rectangle(rbox(x,y,w,h),fill=color,outline='#244052',width=1)
        if ref.startswith(('U','J','L','F','Q','SW')):dr.text(xy(x,y+h+.2),ref,font=ft(11),fill='#173b53')
def onboard(lines,x,y):
    for i,line in enumerate(lines):dr.text(xy(x,y+i*3.1),line,font=ft(16,True),fill='#244052')

# Pi position is explained in the key; avoid text over the relocated 5 V cell.

dr.text(xy(42,235),'FRONT / STEERING',font=ft(17,True),fill='#16354e')
dr.text(xy(38,TOP-5),'REAR / DRIVE MOTORS',font=ft(17,True),fill='#16354e')
side=[('What this establishes',[
    'Actual footprint sizes and saved locations.',
    'Pi underneath; top-side parts overlap it.',
    'A board-size proposal to check on the car.']),
    ('Mounting proposals',[
    'H1/H2: selected rear CAD pair A1/A2.',
    'Front 47.870 mm; rear 73.015 mm.',
    'H5-H8: Pi mounting pattern, 58 x 49 mm.',
    'Rows 233.212 mm apart; centers aligned.']),
    ('Planned electrical connections',[
    'Every placed pad retains its schematic net.',
    'Signal and supply connections routed.',
    'J70: underside socket mates Pi pins 3-38.',
    'No GPIO cable. Pin geometry checked.']),
    ('Remaining layout work',[
    'Review power loops and return paths.',
    'Qualify motor protection and cooling.',
    '1 oz copper; 0.15 mm buck-pad exception.',
    'Check pack mounting and cable space.',
    'Chassis / Pi hole-edge gaps: 4 / 3 mm.']),
    ('Placement key',[
    'Blue block: Pi mounted BELOW this area.',
    'Orange connector: socket on underside.',
    'Pink: preliminary antenna review area.',
    'Amber block: provisional hardware space.',
    'Dark outlines: real component footprints.',
    'Battery pack mounts separately; no holder',
    'fit is claimed on this PCB.'])]
y=190
for title,lines in side:
    dr.text((860,y),title,font=ft(25,True),fill='#16354e');y+=43
    for line in lines:dr.text((860,y),line,font=ft(20),fill='#334b60');y+=30
    y+=38
dr.text((75,1750),'Rear pair selected and measured on the car. Earlier paper fit used the previous hole pattern.',font=ft(20),fill='#334b60')
dr.text((75,1790),'Source: KiCad coordinates and course CAD. Power qualification and final exports remain.',font=ft(20),fill='#334b60')
img.save(ROOT/'Placement-overview.png')

pdf=canvas.Canvas(str(ROOT/'Placement-fit-template.pdf'),pagesize=(210*mm,297*mm))
pdf.setTitle('Lab 4 - 1:1 PCB fit template - provisional')
pdf.setFont('Helvetica-Bold',14);pdf.drawString(15*mm,287*mm,'Lab 4 - revised PCB fit template')
pdf.setFont('Helvetica',9);pdf.drawString(15*mm,281*mm,'Print at 100% / Actual size. Check the 50 mm bar before comparing with the car.')
pdf.setFont('Helvetica-Bold',9);pdf.drawString(15*mm,275*mm,'SELECTED CAD HOLE CENTERS - PLACEMENT PREVIEW - NOT FOR FABRICATION')
BX=45;BY=18
def p_rect(x,y,w,h,fill=None,stroke='#577386'):
    pdf.setStrokeColor(HexColor(stroke));pdf.setLineWidth(.15*mm)
    if fill:pdf.setFillColor(HexColor(fill))
    pdf.rect((BX+x-LEFT)*mm,(BY+BOTTOM-y-h)*mm,w*mm,h*mm,fill=int(fill is not None),stroke=1)
p_rect(LEFT,TOP,d['width_mm'],d['height_mm'],None,'#000000')
pdf.setFillColor(HexColor('#000000'));pdf.setFont('Helvetica-Bold',8)
pdf.drawString(45*mm,269*mm,'REAR / DRIVE MOTORS - new rear pair A1/A2')
pdf.drawCentredString(105*mm,15*mm,'FRONT / STEERING WHEELS')
for r in d['reservations']:
    if r['kind']!='clearance':p_rect(r['x'],r['y'],r['w'],r['h'],colors[r['kind']])
for c in d['components']:
    ref=c['reference']
    if c['schematic'] or ref.startswith('HS'):
        p_rect(*c['bbox'],None,'#648293')
    else:
        cx=(BX+c['x_mm']-LEFT)*mm;cy=(BY+BOTTOM-c['y_mm'])*mm
        pdf.setStrokeColor(HexColor('#000000'));pdf.setLineWidth(.2*mm)
        pdf.circle(cx,cy,c['finished_drill_mm']/2*mm)
        pdf.line(cx-2.5*mm,cy,cx+2.5*mm,cy);pdf.line(cx,cy-2.5*mm,cx,cy+2.5*mm)
        pdf.setFillColor(HexColor('#000000'));pdf.setFont('Helvetica-Bold',7)
        pdf.drawString(cx+2*mm,cy+2*mm,ref)
pdf.setFillColor(HexColor('#183b55'));pdf.setFont('Helvetica-Bold',10)
pdf.setFont('Helvetica',7);pdf.drawCentredString(115*mm,115*mm,'Pi BELOW PCB / H5-H8 supports')
pdf.setFillColor(HexColor('#000000'));pdf.setFont('Helvetica',8)
pdf.drawString(15*mm,8*mm,'H1-H4: 4.0 mm PCB drills for M3. Rear chassis holes: 3.2 mm in CAD. PCB: 120 x 247.212 mm.')
pdf.setLineWidth(.4*mm);pdf.line(20*mm,30*mm,20*mm,80*mm)
pdf.line(18*mm,30*mm,22*mm,30*mm);pdf.line(18*mm,80*mm,22*mm,80*mm)
pdf.saveState();pdf.translate(16*mm,30*mm);pdf.rotate(90)
pdf.drawString(0,0,'This bar must measure 50 mm.');pdf.restoreState()

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
sd.text((728,425),'16.4 mm',font=ft(20),fill='#263441')
def dimension(x,y1,y2,label,small=None):
    sd.line((x,y1,x,y2),fill='#235271',width=2)
    for y in (y1,y2):sd.line((x-8,y,x+8,y),fill='#235271',width=2)
    sd.text((x+17,(y1+y2)/2-17),label,font=ft(24,True),fill='#16354e')
    if small:sd.text((x+17,(y1+y2)/2+16),small,font=ft(18),fill='#334b60')
dimension(1130,280,550,'22 mm','Pi-to-PCB gap')
dimension(1130,571,700,'11.4 mm','before underside parts')
sd.text((60,825),'35 mm chassis standoffs proposed. Caliper heights recorded; final mating is checked at assembly.',font=ft(23),fill='#9b4800')
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
pdf.setFont('Helvetica-Bold',8);pdf.drawString(31*mm,244*mm,'Pi pin1: inner row / leave pair1-2 unused')
pdf.drawString(34*mm,220*mm,'Raspberry Pi 4: 85 x 56 mm')
pdf.drawString(34*mm,215*mm,'58 x 49 mm hole centers')
pdf.setFont('Helvetica',9)
for i,line in enumerate(['USB / Ethernet face right.', 'GPIO row faces the REAR.', 'Socket mates Pi pins3-38 only.', 'Do not use this as a drill guide.', 'Main-PCB Pi origin: (30,89) mm.']):
    pdf.drawString(113*mm,(251-i*7)*mm,line)
pdf.drawImage(str(ROOT/'Pi-stack-side-view.png'),15*mm,83*mm,width=180*mm,height=108*mm)
pdf.setFont('Helvetica-Bold',10);pdf.drawString(15*mm,73*mm,'Recorded geometry and remaining fit checks:')
pdf.setFont('Helvetica',9)
for i,line in enumerate(['Chassis spacers: 35 mm nominal; four-hole paper fit passed with ~50 mm spacers.',
    'Pi-to-PCB gap: 22 mm nominal; calculated socket engagement 5.17 mm.',
    'Reported underside parts <5 mm; calculated nominal metal clearance 6.4 mm.',
    'USB top measured ~18 mm from Pi board bottom; check any added cooler.',
    'Measured chassis pattern retained per team-relayed Ayaan decision; 4 mm drills.',
    'Still check unknown plug/cable/steering envelopes and assembled socket fit.']):
    pdf.drawString(15*mm,(65-i*7)*mm,line)
pdf.setFont('Helvetica',7);pdf.drawString(15*mm,16*mm,'Pi hardware OD <=5.5 mm. Chassis / Pi edge exclusions: 4 / 3 mm. Socket first pair aligns to Pi3/4.')
pdf.save()
print('Created direct-Pi placement overview, side view and two-page true-size fit template.')
