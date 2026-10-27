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
parser.add_argument('--review-gap-mm', type=float, default=.15,
                    help='Nominal drill-edge to zero-margin aperture screen')
args = parser.parse_args()
assert args.review_gap_mm >= 0
board = p.LoadBoard(str(args.board))
lands = [a for f in board.GetFootprints() for a in f.Pads()
         if a.GetAttribute() == p.PAD_ATTRIB_SMD]
rows = []
near_openings = []
apertures = []
for pad in lands:
    for copper, mask, paste in ((p.F_Cu, p.F_Mask, p.F_Paste),
                                (p.B_Cu, p.B_Mask, p.B_Paste)):
        if not pad.IsOnLayer(copper):
            continue
        margin = pad.GetSolderPasteMargin(copper)
        apertures.append(dict(
            pad=pad.GetParentFootprint().GetReference()+'.'+pad.GetNumber(),
            layer=board.GetLayerName(copper),
            mask_present=pad.IsOnLayer(mask), paste_present=pad.IsOnLayer(paste),
            mask_expansion_mm=p.ToMM(pad.GetSolderMaskExpansion(copper)),
            paste_margin_mm=[p.ToMM(margin.x), p.ToMM(margin.y)]))
via_tenting = Counter()
for via in board.GetTracks():
    if via.Type() != p.PCB_VIA_T:
        continue
    # A detached temporary via supplies the exact circular drill shape. It is
    # never added to the board, and no fabrication dimension is changed.
    hole = p.PCB_VIA(board)
    hole.SetPosition(via.GetPosition())
    hole.SetWidth(via.GetDrill())
    drill_shape = hole.GetEffectiveShape(p.F_Cu)
    for layer in (p.F_Cu, p.B_Cu):
        via_tenting[board.GetLayerName(layer)+'_tented' if via.IsTented(layer)
                    else board.GetLayerName(layer)+'_open'] += 1
    search_box = via.GetBoundingBox()
    search_box.Inflate(p.FromMM(args.review_gap_mm))
    for pad in lands:
        if not search_box.Intersects(pad.GetBoundingBox()):
            continue
        for layer in (p.F_Cu, p.B_Cu):
            if not pad.IsOnLayer(layer):
                continue
            margin = pad.GetSolderPasteMargin(layer)
            # With zero mask/paste expansion the copper shape also describes
            # those nominal apertures. Nonzero margins are reported separately.
            if (pad.GetSolderMaskExpansion(layer) == 0 and
                    margin.x == 0 and margin.y == 0 and
                    drill_shape.Collide(pad.GetEffectiveShape(layer), p.FromMM(args.review_gap_mm))):
                near_openings.append(dict(
                    pad=pad.GetParentFootprint().GetReference()+'.'+pad.GetNumber(),
                    via_uuid=via.m_Uuid.AsString(),
                    layer=board.GetLayerName(layer)))
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
    mask_paste_configuration=dict(
        checked_smd_pad_sides=len(apertures),
        via_tenting_counts=dict(sorted(via_tenting.items())),
        nonzero_margin_pad_sides=[r for r in apertures if
            r['mask_expansion_mm'] != 0 or any(r['paste_margin_mm'])],
        pad_sides_without_direct_mask_or_paste=[r for r in apertures if
            not (r['mask_present'] and r['paste_present'])],
        separate_paste_only_pads=[dict(reference=f.GetReference(),
            number=a.GetNumber(), size_mm=[p.ToMM(a.GetSize().x), p.ToMM(a.GetSize().y)],
            x_mm=p.ToMM(a.GetPosition().x), y_mm=p.ToMM(a.GetPosition().y))
            for f in board.GetFootprints() for a in f.Pads()
            if (a.IsOnLayer(p.F_Paste) or a.IsOnLayer(p.B_Paste)) and
            not (a.IsOnLayer(p.F_Cu) or a.IsOnLayer(p.B_Cu))],
        nominal_drill_to_zero_margin_opening_review_gap_mm=args.review_gap_mm,
        nominal_drills_within_review_gap=sorted(near_openings,
            key=lambda r: (r['pad'], r['via_uuid'])),
        note=f'{args.review_gap_mm:g} mm screens nominal drill separation against published hole-position/diameter allowances; it does not qualify mask registration or tenting.'),
    method='Nominal circular via drill intersects actual SMD copper-pad shape.',
    limitations=[
        'No drill/registration tolerance or exported-Gerber/stencil inspection.',
        'Aperture separation uses copper shape only where effective mask/paste margins are zero; inspect other margins separately.',
        'Tenting settings are design requests, not a guarantee of a sealed hole.',
        'A net match or ordinary DRC pass does not qualify solder wicking.',
        'Resolve listed sites by routing changes or explicitly qualified fabrication/assembly treatment; do not assume tenting equals filling/capping.',
    ])
args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in
                  ['status', 'intersecting_vias', 'affected_pads', 'counts_by_net']}, indent=2))
