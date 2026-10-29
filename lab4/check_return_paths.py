"""Read saved copper for a limited ground/feedback/current-sense review.

Run with KiCad Python. This is not a signal-integrity, current-rating or
fabrication release test. Native DRC remains the island-continuity check.
"""
from pathlib import Path
import argparse
import pcbnew as p,json,math,hashlib
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board',type=Path,default=ROOT/'KiCad/Lab4.kicad_pcb')
parser.add_argument('--output',type=Path,default=ROOT/'Return-path-check.json')
args=parser.parse_args()
source=args.board;b=p.LoadBoard(str(source));b.BuildConnectivity();cn=b.GetConnectivity()
fps={f.GetReference():f for f in b.GetFootprints()};pads={(f.GetReference(),a.GetNumber()):a for f in b.GetFootprints() for a in f.Pads()}
def xy(q):return (p.ToMM(q.x),p.ToMM(q.y))
def explicit(a,c):
 # Exclude zones during traversal, not after the full component is returned.
 seen={x.m_Uuid.AsString() for x in cn.GetConnectedItems(a,p.EXCLUDE_ZONES)
       if x.GetNetCode()==a.GetNetCode()}
 seen.add(a.m_Uuid.AsString())
 return c.m_Uuid.AsString() in seen
ground_sites=[xy(t.GetPosition()) for t in b.GetTracks() if t.Type()==p.PCB_VIA_T and t.GetNetname()=='/GND']
ground_sites += [xy(a.GetPosition()) for a in pads.values() if a.GetNetname()=='/GND' and a.GetAttribute()==p.PAD_ATTRIB_PTH]
plane=next(z.GetFilledPolysList(p.In1_Cu) for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer()==p.In1_Cu)
can=[]
for net in ['/CAN_A_H','/CAN_A_L','/CAN_B_H','/CAN_B_L']:
 vias=[t for t in b.GetTracks() if t.Type()==p.PCB_VIA_T and t.GetNetname()==net]
 distances=[dict(x_mm=round(xy(t.GetPosition())[0],3),y_mm=round(xy(t.GetPosition())[1],3),nearest_ground_transition_mm=round(min(math.dist(xy(t.GetPosition()),q) for q in ground_sites),3)) for t in vias]
 gaps=[]
 for t in b.GetTracks():
  if t.GetNetname()!=net or t.Type()!=p.PCB_TRACE_T:continue
  a,c=xy(t.GetStart()),xy(t.GetEnd());n=max(1,math.ceil(math.dist(a,c)/.5))
  for i in range(n+1):
   q=(a[0]+(c[0]-a[0])*i/n,a[1]+(c[1]-a[1])*i/n)
   if not plane.Contains(p.VECTOR2I(p.FromMM(q[0]),p.FromMM(q[1]))):gaps.append(q)
 can.append(dict(net=net,signal_vias=distances,reference_void_sample_count=len(gaps),reference_void_samples_mm=gaps[:40]))
feedback=[]
for u,r in [('U40','R411'),('U41','R421'),('U42','R431')]:
 a,c=pads[(r,'2')],pads[(u,'3')]
 assert a.GetNetname()==c.GetNetname()=='/GND'
 feedback.append(dict(regulator=u,lower_feedback_resistor=r,pad_center_distance_mm=round(math.dist(xy(a.GetPosition()),xy(c.GetPosition())),3),explicit_copper_path_excluding_zones=explicit(a,c),interpretation='A zone-free path is a connectivity test, not proof of an isolated quiet Kelvin return.'))
sense=[]
for r,u in [('R1','U1')]:
 for rp,up in [('1','3'),('2','4')]:
  a,c=pads[(r,rp)],pads[(u,up)];same=a.GetNetname()==c.GetNetname()
  sense.append(dict(shunt_pad=r+'.'+rp,amplifier_pad=u+'.'+up,same_net=same,explicit_copper_path_excluding_zones=explicit(a,c) if same else False))
report=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),fabrication_release=False,can=can,feedback=feedback,current_sense=sense,motor_sensors='U2/U3 are ACS712 magnetic current sensors, not external-shunt amplifiers; their high-current paths need separate routing/width review.',limitations=['Plane-centerline samples include normal pad/via antipads. Each reported void requires geometric interpretation, not an automatic failure.','Ground-transition distances are inspection data, not a certified signal-integrity criterion.','Shared high-current copper and final load currents still need review. No waveform or thermal measurements are claimed.'])
args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(feedback=feedback,current_sense=sense,can=[dict(net=r['net'],max_ground_transition_mm=max([x['nearest_ground_transition_mm'] for x in r['signal_vias']] or [0]),void_samples=r['reference_void_sample_count']) for r in can]),indent=2))
