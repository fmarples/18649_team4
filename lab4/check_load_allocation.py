"""Allocate currents to a shared supply-routing tree with KiCad Python.

This is an assumed-load screening calculation, not a nodal load-flow solution,
thermal qualification or fabrication release. See Supply-path-review.md.
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
parser.add_argument('--output', type=Path, default=ROOT / 'Load-allocation-check.json')
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



cache={}
def tree(net,source):
 key=net,source
 if key in cache:return cache[key]
 items,adj=conductor_graph(net);index={x.m_Uuid.AsString():i for i,x in enumerate(items)};s=index[pads[source].m_Uuid.AsString()];dist={s:0};prev={};q=[(0,s)]
 while q:
  v,i=heapq.heappop(q)
  if v!=dist[i]:continue
  for j in adj[i]:
   val=v+resistance(items[j])
   if val<dist.get(j,1e99):dist[j]=val;prev[j]=i;heapq.heappush(q,(val,j))
 cache[key]=items,index,s,dist,prev
 return cache[key]
def route(net,source,target):
 items,index,s,dist,prev=tree(net,source);j=index[pads[target].m_Uuid.AsString()];out=[]
 while j!=s:out.append(j);j=prev[j]
 return out
def allocation(net,source,loads,minimum):
 items,index,s,dist,prev=tree(net,source);flows={};paths={}
 for ref,pins,amps,basis in loads:
  # Put all package current on its highest-resistance supply pin for screening.
  pin=max(pins,key=lambda n:dist[index[pads[(ref,n)].m_Uuid.AsString()]])
  path=route(net,source,(ref,pin));paths[ref]=(pin,path,amps,basis)
  for j in path:flows[j]=flows.get(j,0)+amps
 rows=[]
 for ref,(pin,path,amps,basis) in paths.items():
  drop=sum(flows[j]*resistance(items[j]) for j in path)
  rows.append(dict(ref=ref,pin=pin,allocation_A=amps,basis=basis,path_R_ohm=round(sum(resistance(items[j]) for j in path),6),shared_tree_drop_V=round(drop,6),static_source_minus_drop_V=round(minimum-drop,6)))
 return dict(net=net,total_allocated_A=round(sum(l[2] for l in loads),6),source_minimum_V=minimum,loads=rows,total_tree_loss_W=round(sum(flows[j]**2*resistance(items[j]) for j in flows),6),largest_drop_V=max(r['shared_tree_drop_V'] for r in rows))
logic=[]
for r in ['U50','U60']:logic.append((r,['1','19','32','48','64'],.070,'70mA allocation: MCU internal maximum plus ADC and GPIO/indicator allowance; not measured'))
for r in ['U10','U14','U20','U24','U30','U34']:logic.append((r,['20'],.010,'10mA datasheet maximum at specified 5.5V/25MHz test; used as planning allowance at 3.3V/16MHz'))
for r in ['U11','U15','U21','U25','U31','U35']:logic.append((r,['3'],.077,'17mA no-load maximum + 3.6V/60ohm=60mA bus-drive allocation; all six allocated simultaneously'))
logic.extend([('U81',['14'],.005,'5mA switching allowance, not measured'),('U1',['5'],.001,'1mA allowance')])
for f in board.GetFootprints():
 if f.GetReference().startswith('R'):
  ps=[a for a in f.Pads() if a.GetNetname()=='/+3V3']
  if ps:
   val=45300 if f.GetReference()=='R430' else 10000
   logic.append((f.GetReference(),[ps[0].GetNumber()],3.6/val,'Conservative shorted-low load at 3.6V; feedback divider separately bounded by top resistor'))
power_report = json.loads((ROOT/'Power-stage-check.json').read_text())
assert power_report['source_sha256']['KiCad/Lab4.kicad_pcb'] == hashlib.sha256(args.board.read_bytes()).hexdigest(), 'Run check_power_stage.py for the current board first'
corner=power_report['regulators']
out=dict(source_sha256=hashlib.sha256(args.board.read_bytes()).hexdigest(),fabrication_release=False,method='Least-resistance predecessor tree with summed downstream load currents. Full item lengths counted. Parallel copper, pad spreading and ground returns omitted. This is a branch-allocation screen, not nodal DC or thermal simulation.',logic=allocation('/+3V3',('L3','2'),logic,corner[2]['static_reference_and_resistor_corners_V'][0]))
loads5=[('U82',['2'],.040004,'40mA encoder planning load plus4uA maximum quiescent allowance'),('J70',['4'],3.0,'Pi planning allocation through physical pin4; socket covers pins3-38'),('U80',['9'],.040,'L298 logic allowance'),('U2',['8'],.015,'ACS712 allowance'),('U3',['8'],.015,'ACS712 allowance')]
for r in ['R570','R571','R670','R671']:loads5.append((r,['1'],5.25/220,'Lamp resistor zero-forward-drop bound, not nominal LED current'))
loads5.append(('R420',['1'],5.25/75000,'Feedback divider bounded by top resistor alone'))
out['five_volt']=allocation('/+5V',('L2','2'),loads5,corner[1]['static_reference_and_resistor_corners_V'][0])
# Conservative regulator envelope: +/-3% full-temperature accuracy,
# +/-1.5% full-load regulation and +/-0.1%/V across the entire 6V input span.
# Their arithmetic sum is deliberately pessimistic; no transient/ground loss included.
encoder_min=4*(1-.03-.015-.006)
out['encoder']=allocation('/Rear zone/ENC_4V',('U82','3'),[(r,['1'],.020,'20mA planning allowance per encoder; not measured') for r in ['J82','J83']],encoder_min)
out['encoder_regulator_screen']={'output_envelope_V':[encoder_min,4*(1+.03+.015+.006)],'dropout_headroom_V':next(r['static_source_minus_drop_V'] for r in out['five_volt']['loads'] if r['ref']=='U82')-(4*(1+.03+.015+.006)+.35),'rated_output_A':.250,'planning_output_A':.040,'thermal_model_W':(5.25-encoder_min)*.040+5.25*.000004,'TO92_theta_JA_C_per_W':131.9,'limitations':'Datasheet extreme sums and allocated loads; not measured load/line/transient behavior.'}
assert out['encoder_regulator_screen']['dropout_headroom_V']>0
assert min(r['static_source_minus_drop_V'] for r in out['encoder']['loads'])>3.3
# Topological independence of dedicated sense traces from the servo load route.
a=route('/+6V6_SERVO',('L1','2'),('R1','1'));k=route('/+6V6_SERVO',('R1','1'),('U1','3'))
c=route('/Front zone/SERVO_VPLUS',('R1','2'),('J90','2'));d=route('/Front zone/SERVO_VPLUS',('R1','2'),('U1','4'))
def conductor_ids(net, source, path):
    items = tree(net, source)[0]
    return {items[j].m_Uuid.AsString() for j in path
            if items[j].Type() in (p.PCB_TRACE_T, p.PCB_VIA_T)}
out['sense_path_shared_conductor_counts']={
    'high_side':len(conductor_ids('/+6V6_SERVO',('L1','2'),a) &
                    conductor_ids('/+6V6_SERVO',('R1','1'),k)),
    'low_side':len(conductor_ids('/Front zone/SERVO_VPLUS',('R1','2'),c) &
                   conductor_ids('/Front zone/SERVO_VPLUS',('R1','2'),d))}
args.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2),flush=True)
