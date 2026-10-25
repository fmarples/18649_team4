"""Run fresh KiCad checks and report fabrication blockers without changing CAD.

Run with KiCad's bundled Python (pcbnew), for example:
  python check_fabrication.py --kicad-cli /path/to/kicad-cli --output-dir /tmp/lab4-check

Exit 0 means the automated checks passed, not that the board is released.
Mechanical, electrical-rating and TA reviews still require engineering judgment.
Exit 1 means design checks found blockers; exit 2 means a tool failed to run.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, output):
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    if result.returncode != 0 or not output.is_file():
        raise RuntimeError(f"Command failed ({result.returncode}): {command}\n"
                           f"{result.stdout}\n{result.stderr}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # A failed tool run must not reuse reports from an earlier successful run.
    if any((out / name).exists() for name in ['netlist.xml', 'erc.json', 'drc.json', 'summary.json']):
        parser.error('Use an empty output directory; old reports must not be mistaken for fresh results.')
    cad = ROOT / 'KiCad'
    sources = sorted(set(cad.glob('*.kicad_sch')) | set(cad.glob('*.kicad_sym')) |
                     set(cad.glob('*.kicad_mod')) | set(cad.glob('*.pretty/*.kicad_mod')) |
                     {cad/'Lab4.kicad_pcb', cad/'Lab4.kicad_pro', cad/'Lab4.kicad_dru',
                      cad/'fp-lib-table', cad/'sym-lib-table'})
    before = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in sources}
    run([args.kicad_cli, 'sch', 'export', 'netlist', '--format', 'kicadxml',
         '-o', str(out/'netlist.xml'), str(cad/'Lab4.kicad_sch')], out/'netlist.xml')
    run([args.kicad_cli, 'sch', 'erc', '--format', 'json', '--severity-all',
         '-o', str(out/'erc.json'), str(cad/'Lab4.kicad_sch')], out/'erc.json')
    run([args.kicad_cli, 'pcb', 'drc', '--format', 'json', '--severity-all',
         '--schematic-parity', '--refill-zones', '-o', str(out/'drc.json'),
         str(cad/'Lab4.kicad_pcb')], out/'drc.json')
    # Deliberately omit --save-board: zone refill is checked in memory only.
    after = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in sources}
    if before != after:
        raise RuntimeError('CAD sources changed during the check; do not use mixed-revision results.')

    erc = json.loads((out/'erc.json').read_text())
    drc = json.loads((out/'drc.json').read_text())
    tree = ET.parse(out/'netlist.xml').getroot()
    components = {c.attrib['ref']: c for c in tree.findall('components/comp')}
    board = pcbnew.LoadBoard(str(cad/'Lab4.kicad_pcb'))
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    unassigned = sorted(r for r, c in components.items() if not c.findtext('footprint'))
    missing = sorted(set(components)-set(footprints))
    board_only = sorted(set(footprints)-set(components))
    erc_findings = list(erc.get('violations', []))
    for sheet in erc.get('sheets', []):
        erc_findings.extend(sheet.get('violations', []))
    counts = {
        'schematic_components': len(components),
        'electrical_footprints': len(set(components) & set(footprints)),
        'track_segments_and_vias': len(board.GetTracks()),
        'copper_zones': sum(not z.GetIsRuleArea() for z in board.Zones()),
        'erc_findings': len(erc_findings),
        'drc_violations': len(drc.get('violations', [])),
        'unconnected_items': len(drc.get('unconnected_items', [])),
        'schematic_parity_findings': len(drc.get('schematic_parity', [])),
    }
    blockers = []
    if unassigned: blockers.append('Assign and verify footprints for: '+', '.join(unassigned))
    if missing: blockers.append('Add missing board components: '+', '.join(missing))
    for key in ['erc_findings', 'drc_violations', 'unconnected_items', 'schematic_parity_findings']:
        if counts[key]: blockers.append(f"{key}: {counts[key]} (inspect the fresh detailed report)")
    if not counts['track_segments_and_vias']: blockers.append('No routing exists on the board.')
    if not counts['copper_zones']: blockers.append('No ground/power copper zones exist on the board.')
    parity_types = Counter(v.get('type', 'unknown') for v in drc.get('schematic_parity', []))
    summary = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'automated_status': 'BLOCKED' if blockers else 'PASS',
        'fabrication_release': False,
        'counts': counts,
        'unassigned_footprints': unassigned,
        'missing_board_components': missing,
        'board_only_references': board_only,
        'schematic_parity_types': dict(parity_types),
        'blockers': blockers,
        'ignored_drc_checks': drc.get('ignored_checks', []),
        'ignored_erc_checks': erc.get('ignored_checks', []),
        'source_sha256': before,
        'limits': [
            'PASS is not release authorization. Complete the engineering review in Fabrication-review.md.',
            'Excluded findings are requested; project-level ignored DRC checks are listed for manual review.',
            'No physical fit, current rating, transient response, thermal behavior or TA approval is inferred.',
            'No CAD changes, manufacturing files, purchase or submission are made by this check.',
        ],
    }
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ['automated_status', 'counts', 'blockers']}, indent=2))
    return bool(blockers)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f'CHECK FAILED: {exc}', file=sys.stderr)
        sys.exit(2)
