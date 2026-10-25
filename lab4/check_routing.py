"""Verify initial regulator copper connectivity with KiCad's connectivity graph.

Run with KiCad's Python. This checks saved copper, not just schematic net names.
DRC, loop/thermal review and the rest of the board are separate requirements.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import pcbnew as p

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', type=Path, default=ROOT/'KiCad/Lab4.kicad_pcb')
parser.add_argument('--output', type=Path, default=ROOT/'Routing-check.json')
args = parser.parse_args()
source = args.board
board = p.LoadBoard(str(source))
board.BuildConnectivity()
connectivity = board.GetConnectivity()
pads = {(f.GetReference(), a.GetNumber()): a
        for f in board.GetFootprints() for a in f.Pads()}
pad_keys = {a.m_Uuid.AsString(): key for key, a in pads.items()}


def reachable(seed):
    """Walk physically touching copper of the seed's net, including vias/zones."""
    pending, seen, result = [seed], set(), set()
    while pending:
        item = pending.pop()
        uid = item.m_Uuid.AsString()
        if uid in seen:
            continue
        seen.add(uid)
        if uid in pad_keys:
            result.add(pad_keys[uid])
        pending.extend(a for a in connectivity.GetConnectedItems(item)
                       if a.GetNetCode() == seed.GetNetCode())
    return result


checks = []
errors = []
for k in range(3):
    u, ind, j, base = f'U{40+k}', f'L{k+1}', f'J{42+k}', 410+10*k
    groups = {
        'SW': [(u, '2'), (ind, '1')],
        'FB': [(u, '6'), (f'R{base}', '2'), (f'R{base+1}', '1'), (f'C{base+4}', '2')],
        'EN': [(u, '5'), (f'R{base+2}', '2'), (f'R{base+3}', '1')],
        'PG': [(u, '4'), (f'R{base+4}', '2'), (j, '2')],
        'local VIN': [(u, '1'), (f'C{base}', '1'), (f'C{base+1}', '1'), (f'R{base+2}', '1')],
        'local output': [(ind, '2'), (f'C{base+2}', '1'), (f'C{base+3}', '1'),
                         (f'R{base}', '1'), (f'C{base+4}', '1'), (j, '1')],
        'local ground': [(u, '3'), (f'C{base}', '2'), (f'C{base+1}', '2'),
                         (f'C{base+2}', '2'), (f'C{base+3}', '2'),
                         (f'R{base+1}', '2'), (f'R{base+3}', '2'), (j, '3')],
    }
    for name, members in groups.items():
        seed = pads[members[0]]
        same_net = all(pads[m].GetNetCode() == seed.GetNetCode() for m in members)
        missing = sorted(set(members)-reachable(seed))
        if not same_net or missing:
            errors.append({'reference': u, 'group': name, 'same_net': same_net,
                           'unreachable_pads': missing})
        checks.append({'reference': u, 'group': name, 'net': seed.GetNetname(),
                       'pads': ['.'.join(m) for m in members],
                       'physically_connected': same_net and not missing})

tracks = list(board.GetTracks())
vias = [t for t in tracks if t.Type() == p.PCB_VIA_T]
segments = [t for t in tracks if t.Type() == p.PCB_TRACE_T]
assert tracks and vias, 'No initial routing found'
assert len({t.m_Uuid.AsString() for t in tracks}) == len(tracks)
assert all(t.GetStart() != t.GetEnd() for t in segments)
report = {
    'status': 'PASS for local connectivity only' if not errors else 'FAIL',
    'fabrication_release': False,
    'errors': errors,
    'counts': {'track_segments': len(segments), 'through_vias': len(vias),
               'copper_zones': sum(not z.GetIsRuleArea() for z in board.Zones()),
               'full_unconnected_count': connectivity.GetUnconnectedCount(False)},
    'segment_width_counts_mm': dict(Counter(round(p.ToMM(t.GetWidth()), 3) for t in segments)),
    'via_diameter_drill_counts_mm': dict(Counter(
        f'{p.ToMM(v.GetWidth(p.F_Cu)):.2f}/{p.ToMM(v.GetDrill()):.2f}' for v in vias)),
    'checks': checks,
    'remaining': [
        'Regulator inputs and outputs still require board-wide distribution; two PG pull-ups await 3V3.',
        'MCU/CAN, clocks, motor/servo, sensing and other signals are not routed.',
        'Review Kelvin feedback returns, effective capacitance, loop geometry and thermal/current capability.',
        'Power-input, motor protection and heatsink decisions remain open; no fabrication release.'],
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
}
args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'counts': report['counts'], 'errors': errors}, indent=2))
raise SystemExit(bool(errors))
