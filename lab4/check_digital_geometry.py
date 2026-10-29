"""Measure CAN branches, critical analog paths and printed labels with KiCad Python.

Lengths count whole conductor items, not exact extracted transmission lines.
This is not signal-integrity qualification or fabrication release.
"""
from pathlib import Path
import argparse
import hashlib
import heapq
import json
import math
import pcbnew as p

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', type=Path, default=ROOT / 'KiCad/Lab4.kicad_pcb')
parser.add_argument('--output', type=Path, default=ROOT / 'Digital-geometry-check.json')
args = parser.parse_args()
board = p.LoadBoard(str(args.board))
board.BuildConnectivity()
cn = board.GetConnectivity()
pads = {(f.GetReference(), a.GetNumber()): a
        for f in board.GetFootprints() for a in f.Pads()}
rho = 1.72e-8  # ohm metres, nominal copper at approximately 20 C
via_plating_mm = 0.020  # assumption, not verified fabrication thickness
board_thickness_mm = 1.6


def conductor_graph(net):
    """Join only overlapping conductor shapes, not transitive net connectivity.

    KiCad GetConnectedItems can return an entire connected component; it must
    not be used as a direct-neighbour graph for a resistance calculation.
    """
    items = [a for f in board.GetFootprints() for a in f.Pads()
             if a.GetNetname() == net]
    items += [t for t in board.GetTracks() if t.GetNetname() == net]
    layers = (p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu)
    shapes, bins, adjacent, boxes = [], {}, {}, []
    for i, item in enumerate(items):
        shapes.append({layer: item.GetEffectiveShape(layer)
                       for layer in layers if item.IsOnLayer(layer)})
        box = item.GetBoundingBox()
        bounds = (box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom())
        boxes.append(bounds)
        adjacent[i] = set()
        cell = p.FromMM(2)
        for x in range(bounds[0] // cell, bounds[2] // cell + 1):
            for y in range(bounds[1] // cell, bounds[3] // cell + 1):
                bins.setdefault((x, y), []).append(i)
    pairs = set()
    for bucket in bins.values():
        for k, i in enumerate(bucket):
            for j in bucket[k+1:]:
                pairs.add((min(i, j), max(i, j)))
    for i, j in pairs:
        a, b = boxes[i], boxes[j]
        if a[0] > b[2] or b[0] > a[2] or a[1] > b[3] or b[1] > a[3]:
            continue
        if any(shapes[i][layer].Collide(shapes[j][layer], 0)
               for layer in shapes[i].keys() & shapes[j].keys()):
            adjacent[i].add(j)
            adjacent[j].add(i)
    return items, adjacent


def resistance(item):
    if item.Type() == p.PCB_TRACE_T:
        track = p.Cast_to_PCB_TRACK(item)
        thickness = 0.035 if track.GetLayer() in (p.F_Cu, p.B_Cu) else 0.0152
        return rho * p.ToMM(track.GetLength()) / (
            p.ToMM(track.GetWidth()) * thickness) * 1000
    if item.Type() == p.PCB_VIA_T:
        via = p.Cast_to_PCB_VIA(item)
        drill = p.ToMM(via.GetDrill())
        area = math.pi * ((drill + 2 * via_plating_mm)**2 - drill**2) / 4
        return rho * board_thickness_mm / area * 1000
    return 0.0



def xy(q):return [round(p.ToMM(q.x),5),round(p.ToMM(q.y),5)]

def path_between(a,z):
 net=pads[a].GetNetname();assert pads[z].GetNetname()==net
 items,adj=conductor_graph(net);idx={t.m_Uuid.AsString():i for i,t in enumerate(items)}
 s=idx[pads[a].m_Uuid.AsString()];goal=idx[pads[z].m_Uuid.AsString()]
 def cost(t):return p.ToMM(t.GetLength()) if t.Type()==p.PCB_TRACE_T else (1.6 if t.Type()==p.PCB_VIA_T else 0)
 dist={s:0};prev={};q=[(0,s)]
 while q:
  v,i=heapq.heappop(q)
  if v!=dist[i]:continue
  if i==goal:break
  for j in adj[i]:
   c=v+cost(items[j])
   if c<dist.get(j,1e99):dist[j]=c;prev[j]=i;heapq.heappush(q,(c,j))
 if goal not in dist:return dict(source='.'.join(a),target='.'.join(z),net=net,connected=False)
 trail=[];j=goal
 while j!=s:trail.append(items[j]);j=prev[j]
 return dict(source='.'.join(a),target='.'.join(z),net=net,connected=True,
   length_mm=round(dist[goal],3),vias=sum(t.Type()==p.PCB_VIA_T for t in trail),
   traces=[dict(uuid=t.m_Uuid.AsString(),a=xy(t.GetStart()),z=xy(t.GetEnd()),layer=t.GetLayerName(),width=p.ToMM(t.GetWidth())) for t in trail if t.Type()==p.PCB_TRACE_T])

out=[]
for bus,ends in [('A',[(('JP20','1'),('JP10','1')),(('R202','2'),('R102','2'))]),('B',[(('JP24','1'),('JP14','1')),(('R242','2'),('R142','2'))])]:
 for side,(source,target) in zip('HL',ends):
  net='/CAN_'+bus+'_'+side;items,adj=conductor_graph(net);idx={o.m_Uuid.AsString():i for i,o in enumerate(items)}
  def cost(t):return p.ToMM(t.GetLength()) if t.Type()==p.PCB_TRACE_T else (1.6 if t.Type()==p.PCB_VIA_T else 0)
  def walk(starts):
   dist={j:0 for j in starts};q=[(0,j) for j in starts];heapq.heapify(q);prev={}
   while q:
    v,i=heapq.heappop(q)
    if v!=dist[i]:continue
    for j in adj[i]:
     d=v+cost(items[j])
     if d<dist.get(j,1e99):dist[j]=d;prev[j]=i;heapq.heappush(q,(d,j))
   return dist,prev
  start=idx[pads[source].m_Uuid.AsString()];end=idx[pads[target].m_Uuid.AsString()];dist,prev=walk([start]);main={end};j=end
  while j!=start:j=prev[j];main.add(j)
  branch,_=walk(main);targets=[]
  for key,pad in pads.items():
   if pad.GetNetname()==net:
    j=idx[pad.m_Uuid.AsString()];targets.append(dict(pad='.'.join(key),branch_length_mm=round(branch[j],3)))
  out.append(dict(net=net,source='.'.join(source),target='.'.join(target),main_length_including_full_vias_mm=round(dist[end],3),main_vias=sum(items[j].Type()==p.PCB_VIA_T for j in main),branches=targets,max_branch_mm=max(r['branch_length_mm'] for r in targets)))

can_rows=out
out={'source_sha256':hashlib.sha256(args.board.read_bytes()).hexdigest(),'fabrication_release':False,'method':'Shortest conductor-item paths: whole segments and full 1.6mm vias, not exact extracted transmission-line lengths. CAN branch length stops at bus-side isolation pad; local transceiver copper and jumper are additional.','can_topology':can_rows,'critical_paths':[]}
for i in range(3):
 u=f'U{40+i}';base=410+10*i;l=f'L{1+i}'
 for a,z in [((u,'1'),(f'C{base+1}','1')),((u,'2'),(l,'1')),((u,'6'),(f'R{base}','2')),((f'R{base+1}','2'),(u,'3')),((l,'2'),(f'R{base}','1'))]:
  row=path_between(a,z);row.pop('traces',None);out['critical_paths'].append(row)
for a,z in [(('R1','1'),('U1','3')),(('R1','2'),('U1','4')),(('R1','2'),('J90','2'))]:
 row=path_between(a,z);row.pop('traces',None);out['critical_paths'].append(row)
for k in [10,14,20,24,30,34]:
 for pin,port in [('7','1'),('6','3')]:
  row=path_between((f'U{k+1}',pin),(f'J{k}',port));row.pop('traces',None);out['critical_paths'].append(row)
out['silkscreen_text']=[dict(text=t.GetText(),xy=xy(t.GetPosition()),layer=t.GetLayerName(),size=xy(t.GetTextSize()),stroke_mm=p.ToMM(t.GetTextThickness())) for t in board.GetDrawings() if t.Type()==p.PCB_TEXT_T and t.GetLayer() in [p.F_SilkS,p.B_SilkS]]
args.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('CAN topologies',len(can_rows),'critical paths',len(out['critical_paths']),'board silk texts',len(out['silkscreen_text']))
