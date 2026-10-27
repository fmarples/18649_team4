"""Estimate copper resistance along connected supply paths with KiCad Python.

This is a full-rail-current screening calculation, not a load-flow solution,
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
parser.add_argument('--output', type=Path, default=ROOT / 'Supply-path-check.json')
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


def evaluate(net, source, targets, allocated_current, source_minimum):
    start = pads[source]
    assert start.GetNetname() == net
    items, adjacent = conductor_graph(net)
    indices = {item.m_Uuid.AsString(): i for i, item in enumerate(items)}
    sid = indices[start.m_Uuid.AsString()]
    distance = {sid: 0.0}
    objects = dict(enumerate(items))
    previous = {}
    queue = [(0.0, sid)]
    while queue:
        value, uid = heapq.heappop(queue)
        if value != distance.get(uid):
            continue
        item = objects[uid]
        for oid in adjacent[uid]:
            other = objects[oid]
            cost = value + resistance(other)
            if cost < distance.get(oid, float('inf')):
                objects[oid] = other
                distance[oid] = cost
                previous[oid] = uid
                heapq.heappush(queue, (cost, oid))
    results = []
    native_ids = {a.m_Uuid.AsString() for a in
                  cn.GetConnectedItems(start, p.EXCLUDE_ZONES)}
    for target in targets:
        pad = pads[target]
        assert pad.GetNetname() == net
        uid = indices[pad.m_Uuid.AsString()]
        row = {'target': '.'.join(target), 'connected': uid in distance}
        assert row['connected'] == (pad.m_Uuid.AsString() in native_ids), (
            'Geometry/native connectivity disagreement', net, target)
        if uid in distance:
            path = []
            while uid != sid:
                path.append(objects[uid])
                uid = previous[uid]
            r = distance[indices[pad.m_Uuid.AsString()]]
            row.update(path_resistance_ohm=round(r, 6),
                       drop_if_full_rail_current_A_is_applied_V=round(r * allocated_current, 6),
                       included_trace_length_mm=round(sum(p.ToMM(p.Cast_to_PCB_TRACK(x).GetLength())
                           for x in path if x.Type() == p.PCB_TRACE_T), 3),
                       included_vias=sum(x.Type() == p.PCB_VIA_T for x in path),
                       conductor_loss_if_full_rail_current_A_is_applied_W=round(r * allocated_current**2, 6))
            if source_minimum is not None:
                row['source_minimum_minus_this_drop_V'] = round(source_minimum-r*allocated_current,6)
        results.append(row)
    return dict(net=net, source='.'.join(source), assumed_full_rail_current_A=allocated_current,
                static_source_minimum_V=source_minimum, paths=results)


power_stage = json.loads((ROOT / 'Power-stage-check.json').read_text())
corners = {r['rail']: r for r in power_stage['regulators']}
rails = [
    evaluate('/+3V3', ('L3', '2'),
             [(u, pin) for u in ('U50', 'U60') for pin in ('19', '32', '48', '64')] +
             [(u, '3') for u in ('U11', 'U15', 'U21', 'U25', 'U31', 'U35')],
             corners['3V3']['allocated_output_A'],
             corners['3V3']['static_reference_and_resistor_corners_V'][0]),
    evaluate('/+5V', ('L2', '2'), [('J70', '4'), ('U80', '9'), ('U2', '8'), ('U3', '8'), ('U82','2')],
             corners['5V']['allocated_output_A'],
             corners['5V']['static_reference_and_resistor_corners_V'][0]),
]
rails.append(evaluate('/Rear zone/ENC_4V',('U82','3'),[('J82','1'),('J83','1')],.040,4*(1-.03-.015-.006)))
actuator_paths = [
    evaluate('/+6V6_SERVO', ('L1','2'), [('R1','1')], 4.0,
             corners['SERVO']['static_reference_and_resistor_corners_V'][0]),
    evaluate('/Front zone/SERVO_VPLUS', ('R1','2'), [('J90','2')], 4.0, None),
]
for side, sensor, connector, drive, ret in [
        ('LEFT','U2','J80','2','3'), ('RIGHT','U3','J81','13','14')]:
    actuator_paths += [
        evaluate('/Rear zone/'+side+'_BRIDGE', ('U80',drive),
                 [(sensor,'1'),(sensor,'2')], 3.2, None),
        evaluate('/Rear zone/'+side+'_MOTOR', (sensor,'3'),
                 [(connector,'1')], 3.2, None),
        evaluate('/Rear zone/'+side+'_RETURN', (connector,'2'),
                 [('U80',ret)], 3.2, None),
    ]
report = dict(source_sha256=hashlib.sha256(args.board.read_bytes()).hexdigest(),
              fabrication_release=False, copper_resistivity_ohm_m=rho,
              outer_copper_mm=0.035, inner_copper_mm=0.0152,
              assumed_via_plating_mm=via_plating_mm, rails=rails,
              actuator_paths=actuator_paths,
              actuator_interpretation='Servo uses the provisional 4 A rail allocation. Motor 3.2 A is a catalog stall stress calculation, NOT a permissible L298 operating current. Paths omit shunt/sensor/driver and external cable/contact loss; ground returns are not solved.',
              limitations=[
                  'Counts each traversed segment in full, even when a connection touches its middle; parallel paths are not solved.',
                  'Applies the whole allocated rail current to each path separately; actual branch currents must be assigned for a load-flow result.',
                  'Pad spreading/contact resistance, source-to-inductor loss, ground return and heating are omitted.',
                  'Via plating is assumed. No guarantee of total voltage, thermal current capability or regulator transient response.',
                  'Static regulator corner values are taken from Power-stage-check.json; they omit load/line regulation and transients.'
              ])
args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(rails, indent=2))
