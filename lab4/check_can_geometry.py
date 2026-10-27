"""Measure CAN copper geometry; this is not an impedance or SI qualification.

Run with KiCad Python. Distances are inspection data, not pass/fail limits.
Totals include connector, test and termination branches, not just end-to-end bus.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import pcbnew as p

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', type=Path, default=ROOT/'KiCad/Lab4.kicad_pcb')
parser.add_argument('--output', type=Path, default=ROOT/'CAN-geometry-check.json')
args = parser.parse_args()
b = p.LoadBoard(str(args.board))
def xy(v): return (p.ToMM(v.x), p.ToMM(v.y))
def point_distance(q, t):
    a, z = xy(t.GetStart()), xy(t.GetEnd())
    dx, dy = z[0]-a[0], z[1]-a[1]
    length2 = dx*dx+dy*dy
    f = max(0, min(1, ((q[0]-a[0])*dx+(q[1]-a[1])*dy)/length2)) if length2 else 0
    return math.dist(q, (a[0]+f*dx, a[1]+f*dy))

planes = {}
for layer in (p.In1_Cu, p.B_Cu):
    planes[layer] = [z.GetFilledPolysList(layer) for z in b.Zones()
                     if not z.GetIsRuleArea() and z.GetNetname()=='/GND' and z.IsOnLayer(layer)]
nets = ['/CAN_'+bus+'_'+side for bus in 'AB' for side in 'HL']
tracks = {net: [t for t in b.GetTracks() if t.GetNetname()==net and t.Type()==p.PCB_TRACE_T]
          for net in nets}
records = []
for net in nets:
    other = net[:-1]+('L' if net.endswith('H') else 'H')
    totals = {}
    gaps = []
    samples = []
    own_holes = [xy(t.GetPosition()) for t in b.GetTracks()
                 if t.GetNetname()==net and t.Type()==p.PCB_VIA_T]
    own_holes += [xy(a.GetPosition()) for f in b.GetFootprints() for a in f.Pads()
                  if a.GetNetname()==net and a.GetAttribute()==p.PAD_ATTRIB_PTH]
    for t in tracks[net]:
        length = p.ToMM(t.GetLength()); layer = t.GetLayer()
        totals[t.GetLayerName()] = totals.get(t.GetLayerName(), 0)+length
        a,z = xy(t.GetStart()),xy(t.GetEnd()); n=max(1,math.ceil(length/.5))
        candidates=[u for u in tracks[other] if u.GetLayer()==layer]
        for i in range(n):
            f=(i+.5)/n; q=(a[0]+f*(z[0]-a[0]), a[1]+f*(z[1]-a[1]))
            distance=min((point_distance(q,u) for u in candidates),default=None)
            samples.append((distance,length/n))
            # F.Cu references In1; In2 references nearby B.Cu. Bottom traces
            # have no adjacent solid plane in this stack: review separately.
            ref={p.F_Cu:p.In1_Cu,p.In2_Cu:p.B_Cu}.get(layer)
            near_hole=any(math.dist(q,h)<1.0 for h in own_holes)
            if ref is not None and not near_hole:
                point=p.VECTOR2I(p.FromMM(q[0]),p.FromMM(q[1]))
                if not any(poly.Contains(point) for poly in planes[ref]):
                    gaps.append(dict(x_mm=round(q[0],3),y_mm=round(q[1],3),
                                     signal_layer=t.GetLayerName(),reference_layer=b.GetLayerName(ref)))
    total=sum(w for _,w in samples)
    fraction=lambda limit: round(100*sum(w for d,w in samples if d is not None and d<=limit)/total,2)
    records.append(dict(net=net,branch_inclusive_length_mm=round(total,3),
        length_by_layer_mm={k:round(v,3) for k,v in sorted(totals.items())},
        via_count=sum(t.Type()==p.PCB_VIA_T and t.GetNetname()==net for t in b.GetTracks()),
        trace_widths_mm=sorted(set(round(p.ToMM(t.GetWidth()),3) for t in tracks[net])),
        length_percent_with_opposite_line_on_same_layer_within_0p65mm=fraction(.65),
        length_percent_with_opposite_line_on_same_layer_within_1mm=fraction(1),
        reference_void_samples_away_from_own_holes=gaps))
# Approximate straight front-layer pair only. TI SLVA531A equations 1-2;
# this model omits coplanar fill, solder mask, pads, bends and layer changes.
w,h,t,er,s=.2,.21040,.035,4.4,.4
z0=87/math.sqrt(er+1.41)*math.log(5.98*h/(.8*w+t))
zdiff=2*z0*(1-.48*math.exp(-.96*s/h))
report=dict(source_sha256=hashlib.sha256(args.board.read_bytes()).hexdigest(),
    fabrication_release=False,status='Geometry measured; engineering review required',
    sample_spacing_max_mm=.5,own_pad_via_exclusion_radius_mm=1.0,nets=records,
    straight_front_pair_microstrip_estimate=dict(trace_width_mm=w,edge_gap_mm=s,
        dielectric_height_mm=h,copper_thickness_mm=t,relative_permittivity=er,
        single_ended_ohm=round(z0,2),differential_ohm=round(zdiff,2),
        interpretation='Calculation for the documented nominal main-run dimensions only, not whole-bus or controlled-impedance qualification.'),
    references=['https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf',
                'https://www.ti.com/lit/an/slla270/slla270.pdf',
                'https://www.ti.com/lit/an/slva531a/slva531a.pdf','Layer-stack.md'],
    limitations=['Nearest opposite-line distance does not prove parallel coupled routing or impedance.',
        'Length includes all branches; total H/L difference is not end-to-end timing skew.',
        'Samples test centerlines only and exclude normal own-pad/via antipads within 1 mm.',
        'In2 uses B.Cu fill as its nearest reference. B.Cu traces need separate return review because In2 is a signal layer.',
        'No rise-time, reflection, crosstalk, EMC or propagation-delay measurements are claimed.'])
args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='reference_void_samples_away_from_own_holes'} |
                  {'reference_void_samples':len(r['reference_void_samples_away_from_own_holes'])} for r in records],indent=2))
