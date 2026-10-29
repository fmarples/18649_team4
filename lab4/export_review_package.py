"""Export a hash-checked KiCad review package; never marks fabrication released.

Run after check_fabrication.py and the BOM/placement checks. This creates a new
directory so stale files cannot silently enter a manufacturing archive.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kicad-cli', default='kicad-cli')
    ap.add_argument('--audit-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    audit = json.loads((args.audit_dir/'summary.json').read_text())
    assert audit['automated_status'] == 'PASS'
    for name, digest in audit['source_sha256'].items():
        assert sha(ROOT/name) == digest, f'Stale audit: {name}'
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    gerber = out/'gerbers'
    gerber.mkdir()
    board = ROOT/'KiCad/Lab4.kicad_pcb'
    def cli(*command):
        subprocess.run([args.kicad_cli, *map(str, command)], check=True,
                       cwd=ROOT, timeout=300)
    cli('sch', 'export', 'pdf', '-o', out/'Lab4-Circuits.pdf',
        '--exclude-pdf-property-popups', ROOT/'KiCad/Lab4.kicad_sch')
    cli('pcb', 'export', 'gerbers', '-o', str(gerber)+'/', '-l', LAYERS,
        '--subtract-soldermask', '--check-zones', '--no-protel-ext', board)
    cli('pcb', 'export', 'drill', '-o', str(gerber)+'/', '--format', 'excellon',
        '--drill-origin', 'absolute', '--excellon-units', 'mm',
        '--excellon-separate-th', '--generate-map', '--map-format', 'pdf',
        '--generate-report', '--report-path', out/'Drill-report.txt', board)
    cli('pcb', 'export', 'pdf', '-o', out/'PCB-layers.pdf', '-l', LAYERS,
        '--cl', 'Edge.Cuts', '--mode-multipage', '--subtract-soldermask',
        '--check-zones', '--no-property-popups', '--scale', '0', board)
    cli('pcb', 'export', 'pos', '-o', out/'Positions-native.csv',
        '--format', 'csv', '--units', 'mm', '--side', 'both', board)
    for side in ('top', 'bottom'):
        cli('pcb', 'render', '-o', out/f'PCB-{side}.png', '--side', side,
            '--width', '1600', '--height', '1100', '--background', 'opaque', board)
    for filename in ('summary.json', 'drc.json', 'erc.json'):
        shutil.copy2(args.audit_dir/filename, out/filename)
    for filename in ('BOM-Hand-assembly.csv', 'Preliminary-BOM.csv', 'TEAM_4_BOM_Lab4.xlsx',
                     'Course-stock-v3.csv', 'Layer-stack.md',
                     'Lab4-Writeup.pdf', 'Fabrication-review.md',
                     'Power-margin-review.md', 'Assembly-options.md',
                     'Critical-package-review.md', 'Selected-package-check.json',
                     'Battery-LiPo.md', 'Course-updates-October29.md',
                     'Capacitor-bank-review.md', 'Power-route-revision.md',
                     'Power-route-revision-check.json', 'Fuse-and-scope-review.md',
                     'Pi-feed-review.md', 'Pi-feed-mesh-check.json',
                     'Actuator-design.md', 'Parts-review.md'):
        shutil.copy2(ROOT/filename, out/filename)
    warning = ('REVIEW ONLY - NOT RELEASED FOR FABRICATION\n\n'
        'Four copper layers; nominal 1.6 mm JLC04161H-7628 stack.\n'
        'This is a review export of the hashed sources, not an approved order.\n'
        'See Fabrication-review.md and Power-margin-review.md for open issues.\n'
        '3D views use available library models; omitted custom parts are not fit evidence.\n'
        'Native positions use KiCad rotation conventions and mm/absolute origin.\n'
        'The team hand-assembly plan remains in force. No PCBA upload is authorized.\n')
    (out/'REVIEW-ONLY.txt').write_text(warning, encoding='utf-8')
    with zipfile.ZipFile(out/'Gerbers-REVIEW-ONLY.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(gerber.iterdir()):
            z.write(path, path.name)
        z.writestr('REVIEW-ONLY.txt', warning)
    for name, digest in audit['source_sha256'].items():
        assert sha(ROOT/name) == digest, f'Export changed source: {name}'
    manifest = dict(fabrication_release=False, copper_layers=4,
        source_sha256=audit['source_sha256'],
        files={str(p.relative_to(out)).replace('\\','/'):sha(p)
               for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Review package created: {out}; fabrication_release=False')

if __name__ == '__main__':
    main()
