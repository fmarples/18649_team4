"""Refresh placement previews from the saved routed PCB without changing it.

Run with KiCad Python. Coordinates use the board's (40,40) mm outline origin.
This is a review-data export, not a qualified assembly CPL or drill template.
"""
from pathlib import Path
import csv
import hashlib
import json
import pcbnew as p

root=Path(__file__).resolve().parent
source=root/'KiCad/Lab4.kicad_pcb'
before=source.read_bytes()
board=p.LoadBoard(str(source))
data=json.loads((root/'placement-data.json').read_text(encoding='utf-8'))
with (root/'KiCad/Circuit-BOM.csv').open(encoding='utf-8-sig',newline='') as f:
    electrical={r['Reference'] for r in csv.DictReader(f)}
records=[]
for fp in sorted(board.GetFootprints(),key=lambda f:f.GetReference()):
    fp.BuildCourtyardCaches()
    box=fp.GetCourtyard(p.B_CrtYd if fp.IsFlipped() else p.F_CrtYd).BBox()
    if box.GetWidth()==0: box=fp.GetBoundingBox(False,False)
    records.append(dict(reference=fp.GetReference(),value=fp.GetValue(),
        footprint=fp.GetFPIDAsString(),
        x_mm=round(p.ToMM(fp.GetPosition().x)-40,4),
        y_mm=round(p.ToMM(fp.GetPosition().y)-40,4),
        rotation_deg=fp.GetOrientationDegrees(),layer=fp.GetLayerName(),
        bbox=[p.ToMM(box.GetX())-40,p.ToMM(box.GetY())-40,
              p.ToMM(box.GetWidth()),p.ToMM(box.GetHeight())],
        schematic=fp.GetReference() in electrical))
    if fp.GetReference() in [f'H{i}' for i in range(1,9)]:
        records[-1]['finished_drill_mm']=p.ToMM(next(iter(fp.Pads())).GetDrillSize().x)
        records[-1]['edge_exclusion_mm']=4 if int(fp.GetReference()[1:])<=4 else 3
assert {r['reference'] for r in records if r['schematic']}==electrical
data['components']=records
data['source_sha256']=hashlib.sha256(before).hexdigest()
(root/'placement-data.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
with (root/'Placement-coordinates.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,['reference','value','footprint','x_mm','y_mm','rotation_deg','layer','schematic'],extrasaction='ignore')
    w.writeheader();w.writerows(records)
assert source.read_bytes()==before
print(f'Exported {len(electrical)} electrical footprints; PCB unchanged.')
