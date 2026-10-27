"""Check actual copper and component courtyards 3mm from support-hole edges.

Run with KiCad Python. Empty NPTH drill pads are mechanical holes, not copper.
The saved support rule areas reject tracks, vias and fills; this check also
checks electrical pads explicitly, without treating the holes as violations.
"""
from pathlib import Path
import hashlib
import json
import pcbnew as p

ROOT = Path(__file__).resolve().parent
path = ROOT / 'KiCad/Lab4.kicad_pcb'
b = p.LoadBoard(str(path))
fps = {f.GetReference(): f for f in b.GetFootprints()}
layers = [p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu]
items = list(b.GetTracks()) + [a for f in fps.values() for a in f.Pads()
                              if a.GetAttribute() != p.PAD_ATTRIB_NPTH]
errors, rows = [], []
for i in range(1, 9):
    ref = f'H{i}'
    hole = fps[ref]
    pad = next(iter(hole.Pads()))
    radius = pad.GetDrillSize().x // 2 + p.FromMM(3)
    circle = p.SHAPE_CIRCLE(hole.GetPosition(), radius - p.FromMM(.00001)) # 10nm rounding tolerance
    region = p.BOX2I(hole.GetPosition() - p.VECTOR2I(radius, radius),
                    p.VECTOR2I(2 * radius, 2 * radius))
    for item in items:
        if not region.Intersects(item.GetBoundingBox()):
            continue
        for layer in layers:
            if item.IsOnLayer(layer) and item.GetEffectiveShape(layer).Collide(circle, 0):
                errors.append(dict(hole=ref, kind='copper', uuid=item.m_Uuid.AsString(),
                                   net=item.GetNetname(), layer=b.GetLayerName(layer)))
    for zone in b.Zones():
        if zone.GetIsRuleArea():
            continue
        for layer in layers:
            if zone.IsOnLayer(layer) and zone.GetFilledPolysList(layer).Collide(circle, 0):
                errors.append(dict(hole=ref, kind='zone fill', layer=b.GetLayerName(layer)))
    for name, fp in fps.items():
        if name == ref:
            continue
        fp.BuildCourtyardCaches()
        for layer in [p.F_CrtYd, p.B_CrtYd]:
            court = fp.GetCourtyard(layer)
            if court.OutlineCount() and court.Collide(circle, 0):
                errors.append(dict(hole=ref, kind='component courtyard', reference=name))
    names = [z for z in b.Zones() if z.GetIsRuleArea()
             and z.GetZoneName() == ref + ' 3mm FROM HOLE EDGE / NO COPPER']
    if {z.GetLayer() for z in names} != set(layers):
        errors.append(dict(hole=ref, kind='missing all-layer support rule areas'))
    rows.append(dict(reference=ref, finished_drill_mm=p.ToMM(pad.GetDrillSize().x),
                     minimum_clear_radius_mm=p.ToMM(radius), layers=len(names)))
result = dict(status='PASS' if not errors else 'FAIL',
              pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              rule='3mm from finished hole edge, all chassis/Pi supports',
              holes=rows, errors=errors,
              limits=['Checks the saved filled geometry, not an assembled fit.',
                      'NPTH drill pads are excluded; electrical pads are checked.',
                      'Use hardware within the documented maximum outside diameters.'])
(ROOT / 'Mounting-clearance-check.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(bool(errors))
