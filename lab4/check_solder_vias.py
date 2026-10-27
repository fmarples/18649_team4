"""Inventory via drills intersecting SMD copper lands, using KiCad geometry.

Run with KiCad Python. This reports assembly-review sites; it neither qualifies
via filling/capping nor replaces a solder-mask, paste or fabrication review.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import pcbnew as p

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', type=Path, default=ROOT/'KiCad/Lab4.kicad_pcb')
parser.add_argument('--output', type=Path, default=ROOT/'Solder-via-check.json')
args = parser.parse_args()
board = p.LoadBoard(str(args.board))
lands = [a for f in board.GetFootprints() for a in f.Pads()
         if a.GetAttribute() == p.PAD_ATTRIB_SMD]
rows = []
for via in board.GetTracks():
    if via.Type() != p.PCB_VIA_T:
        continue
    # A detached temporary via supplies the exact circular drill shape. It is
    # never added to the board, and no fabrication dimension is changed.
    hole = p.PCB_VIA(board)
    hole.SetPosition(via.GetPosition())
    hole.SetWidth(via.GetDrill())
    drill_shape = hole.GetEffectiveShape(p.F_Cu)
    for pad in lands:
        if not via.GetBoundingBox().Intersects(pad.GetBoundingBox()):
            continue
        for layer in (p.F_Cu, p.B_Cu):
            if (pad.IsOnLayer(layer) and
                    drill_shape.Collide(pad.GetEffectiveShape(layer), 0)):
                rows.append(dict(
                    pad=pad.GetParentFootprint().GetReference()+'.'+pad.GetNumber(),
                    net=pad.GetNetname(), layer=board.GetLayerName(layer),
                    via_uuid=via.m_Uuid.AsString(),
                    x_mm=round(p.ToMM(via.GetPosition().x), 4),
                    y_mm=round(p.ToMM(via.GetPosition().y), 4),
                    drill_mm=round(p.ToMM(via.GetDrill()), 4)))
                break
rows.sort(key=lambda r: (r['pad'], r['via_uuid']))
report = dict(
    source_sha256=hashlib.sha256(args.board.read_bytes()).hexdigest(),
    fabrication_release=False,
    status='Assembly review required' if rows else 'No drill/land intersections found',
    intersecting_vias=len({r['via_uuid'] for r in rows}),
    affected_pads=len({r['pad'] for r in rows}),
    counts_by_net=dict(sorted(Counter(r['net'] for r in rows).items())),
    intersections=rows,
    method='Nominal circular via drill intersects actual SMD copper-pad shape.',
    limitations=[
        'No drill tolerance, solder-mask opening or paste-aperture analysis.',
        'Vias beside lands can still need solder-mask separation review.',
        'A net match or ordinary DRC pass does not qualify solder wicking.',
        'Resolve listed sites by routing changes or explicitly qualified fabrication/assembly treatment; do not assume tenting equals filling/capping.',
    ])
args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in
                  ['status', 'intersecting_vias', 'affected_pads', 'counts_by_net']}, indent=2))
