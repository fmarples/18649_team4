"""Verify routed regulator, MCU, CAN, host and signal copper with KiCad's graph.

Run with KiCad's Python. This checks saved copper, not just schematic net names.
DRC, loop/thermal review and the rest of the board are separate requirements.
Zone objects can contain multiple filled islands. The grouped-zone graph is
not an island-continuity proof; inspect native DRC's unconnected items too.
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
reachable_cache = {}
physical_reachable_cache = {}


def reachable(seed):
    """Walk physically touching copper of the seed's net, including vias/zones."""
    seed_uid = seed.m_Uuid.AsString()
    if seed_uid in reachable_cache:
        return reachable_cache[seed_uid]
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
    for uid in seen:
        reachable_cache[uid] = result
        physical_reachable_cache[uid] = seen
    return result


checks = []
errors = []
def check_group(reference, name, members):
    seed = pads[members[0]]
    same_net = all(pads[m].GetNetCode() == seed.GetNetCode() for m in members)
    missing = sorted(set(members)-reachable(seed))
    if not same_net or missing:
        errors.append({'reference': reference, 'group': name, 'same_net': same_net,
                       'unreachable_pads': missing})
    checks.append({'reference': reference, 'group': name, 'net': seed.GetNetname(),
                   'pads': ['.'.join(m) for m in members],
                   'physically_connected': same_net and not missing})

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
        check_group(u, name, members)

for n in [10, 14, 20, 24, 30, 34]:
    u, t, j, test, y, base = f'U{n}', f'U{n+1}', f'J{n}', f'J{n+1}', f'Y{n}', n*10
    groups = {
        'OSC1': [(u, '9'), (y, '1'), (f'C{base}', '1')],
        'OSC2': [(u, '8'), (y, '3'), (f'C{base+1}', '1')],
        'RESET': [(u, '19'), (f'C{base+2}', '1'), (f'R{base}', '2')],
        'local supply': [(u, a) for a in ['4', '5', '7', '20']] +
                        [(t, '3'), (f'C{base+3}', '1'), (f'C{base+4}', '1'),
                         (f'R{base}', '1'), (f'R{base+1}', '1')],
        'CS pullup': [(u, '18'), (f'R{base+1}', '2')],
        'TXD': [(u, '1'), (t, '1'), (test, '1')],
        'RXD': [(u, '2'), (t, '4'), (test, '2')],
        'local ground': [(u, '10'), (t, '2'), (t, '8'), (y, '2'), (y, '4')] +
                        [(f'C{base+i}', '2') for i in range(5)],
        'CAN H to isolation': [(t, '7'), (j, '1')],
        'CAN L to isolation': [(t, '6'), (j, '3')],
        'backbone H node': [(j, '2'), (test, '3')],
        'backbone L node': [(j, '4'), (test, '4')],
    }
    if n < 30:
        groups['backbone H node'].append((f'JP{n}', '1'))
        groups['backbone L node'].append((f'R{base+2}', '2'))
        groups['termination resistor'] = [(f'JP{n}', '2'), (f'R{base+2}', '1')]
    for name, members in groups.items():
        check_group(u, name, members)

for n in [50, 60]:
    u, base = f'U{n}', n*10
    groups = {
        'local supply': [(u, a) for a in ['1', '19', '32', '48', '64']] +
                        [(f'C{base+i}', '1') for i in range(6)] +
                        [(f'FB{n}', '1'), (f'R{base+1}', '1'), (f'R{base+2}', '1')],
        'VCAP': [(u, '30'), (f'C{base+6}', '1')],
        'VDDA': [(u, '13'), (f'C{base+7}', '1'), (f'C{base+8}', '1'), (f'FB{n}', '2')],
        'RESET': [(u, '7'), (f'C{base+9}', '1'), (f'R{base+1}', '2'), (f'SW{n}', '1')],
        'self test': [(u, '2'), (f'C{base+10}', '1'), (f'R{base+2}', '2'), (f'SW{n+1}', '1')],
        'BOOT0': [(u, '60'), (f'R{base}', '1')],
        'local ground': [(u, a) for a in ['12', '18', '31', '47', '63']] +
                        [(f'C{base+i}', '2') for i in range(11)] +
                        [(f'R{base}', '2'), (f'SW{n}', '2'), (f'SW{n+1}', '2')],
    }
    for name, members in groups.items():
        check_group(u, name, members)

# Backbone pads must connect across all three zones, with termination on the
# bus side of the isolation jumpers. Local transceiver nets are separate.
for bus in ['A', 'B']:
    for signal in ['H', 'L']:
        net = f'/CAN_{bus}_{signal}'
        members = sorted(key for key, a in pads.items() if a.GetNetname() == net)
        assert len(members) == 8, (net, members)
        check_group(f'CAN_{bus}', f'{signal} backbone', members)

# Check the retained Lab 3 host mapping, including each CS pull-up. The three
# shared SPI signals reach both controllers; CS and INT remain independent.
for host, ca, cb, host_pins in [
        ('U50', 10, 14, ['21', '22', '23', '58', '38', '43', '57']),
        ('U60', 20, 24, ['21', '22', '23', '58', '38', '43', '57']),
        ('J70', 30, 34, ['23', '21', '19', '24', '26', '22', '18'])]:
    for name, hp, cp in zip(['host SCK', 'host MISO', 'host MOSI'],
                            host_pins[:3], ['14', '17', '16']):
        check_group(host, name, [(host, hp), (f'U{ca}', cp), (f'U{cb}', cp)])
    for name, hp, controller in [('host CS A', host_pins[3], ca),
                                 ('host CS B', host_pins[4], cb)]:
        check_group(host, name, [(host, hp), (f'U{controller}', '18'),
                                (f'R{controller*10+1}', '2')])
    for name, hp, controller in [('host INT A', host_pins[5], ca),
                                 ('host INT B', host_pins[6], cb)]:
        check_group(host, name, [(host, hp), (f'U{controller}', '13')])

# Expected endpoints are fixed from the reviewed schematic, not inferred
# from the copper being tested. Supply/load-current paths are separate.
signal_groups = {
    '/Cockpit zone/PI_CMD_TX_MARKER': 'J70.13 J703.4',
    '/Cockpit zone/PI_DEG_A_LED': 'J70.29 J703.7 R712.1',
    '/Cockpit zone/PI_DEG_A_LED_ANODE': 'D712.2 R712.2',
    '/Cockpit zone/PI_DEG_B_LED': 'J70.31 J703.8 R713.1',
    '/Cockpit zone/PI_DEG_B_LED_ANODE': 'D713.2 R713.2',
    '/Cockpit zone/PI_ERROR_LED': 'J70.32 J704.4 R711.1',
    '/Cockpit zone/PI_ERROR_LED_ANODE': 'D711.2 R711.2',
    '/Cockpit zone/PI_SELFTEST_BUTTON': 'C702.1 J70.36 J704.3 R700.2 SW70.1',
    '/Cockpit zone/PI_STATUS_LED': 'J70.33 J704.5 R710.1',
    '/Cockpit zone/PI_STATUS_LED_ANODE': 'D710.2 R710.2',
    '/Cockpit zone/PI_TX_A_MARKER': 'J70.15 J703.5',
    '/Cockpit zone/PI_TX_B_MARKER': 'J70.16 J703.6',
    '/Cockpit zone/PI_UDP_RX_MARKER': 'J70.11 J703.3',
    '/Front zone/F_BOOT0': 'J500.2 R500.1 U50.60',
    '/Front zone/F_DEG_A_LED_ANODE': 'D512.2 R512.2',
    '/Front zone/F_DEG_B_LED_ANODE': 'D513.2 R513.2',
    '/Front zone/F_DIR_A_MARKER': 'J505.4 U50.29',
    '/Front zone/F_ERROR_LED': 'J503.13 J504.4 R511.1 U50.8',
    '/Front zone/F_ERROR_LED_ANODE': 'D511.2 R511.2',
    '/Front zone/F_FRONT_LEFT_LED_BASE': 'Q550.1 R550.2 R560.1',
    '/Front zone/F_FRONT_LEFT_LED_PLUS': 'J550.1 R570.2',
    '/Front zone/F_FRONT_LEFT_LED_SINK': 'J550.2 Q550.3',
    '/Front zone/F_FRONT_RIGHT_LED_BASE': 'Q551.1 R551.2 R561.1',
    '/Front zone/F_FRONT_RIGHT_LED_PLUS': 'J551.1 R571.2',
    '/Front zone/F_FRONT_RIGHT_LED_SINK': 'J551.2 Q551.3',
    '/Front zone/F_PID_MARKER': 'J504.7 U50.40',
    '/Front zone/F_PWM_SET_MARKER': 'J505.3 U50.62',
    '/Front zone/F_RELAY_TX_MARKER': 'J503.12 U50.37',
    '/Front zone/F_RESET_N': 'C509.1 J501.5 R501.2 SW50.1 U50.7',
    '/Front zone/F_SELFTEST_BUTTON': 'C510.1 J504.3 R502.2 SW51.1 U50.2',
    '/Front zone/F_SERVO_PWM': 'J503.9 R530.1 R540.1 U50.42',
    '/Front zone/F_STATUS_LED_ANODE': 'D510.2 R510.2',
    '/Front zone/F_SWCLK': 'J501.2 U50.49',
    '/Front zone/F_SWDIO': 'J501.4 U50.46',
    '/Front zone/SERVO_ADC': 'C2.1 J1.2 J504.8 R2.2 U50.16',
    '/Front zone/SERVO_PWM_OUT': 'J90.3 R540.2',
    '/Front zone/SERVO_RAW': 'J1.1 R2.1 U1.1',
    '/Rear zone/LEFT_ADC': 'C5.1 J2.3 J604.10 R5.2 U60.16',
    '/Rear zone/LEFT_ENC_A_IN': 'R800.2 U81.1',
    '/Rear zone/LEFT_ENC_A_RAW': 'J82.3 R800.1 R804.2',
    '/Rear zone/LEFT_ENC_B_IN': 'R801.2 U81.3',
    '/Rear zone/LEFT_ENC_B_RAW': 'J82.4 R801.1 R805.2',
    '/Rear zone/LEFT_FILTER': 'C4.1 U2.6',
    '/Rear zone/LEFT_RAW': 'J2.1 R3.1 U2.7',
    '/Rear zone/LEFT_SCALED': 'J2.2 R3.2 R4.1 R5.1',
    '/Rear zone/RIGHT_ADC': 'C8.1 J3.3 J604.11 R8.2 U60.17',
    '/Rear zone/RIGHT_ENC_A_IN': 'R802.2 U81.5',
    '/Rear zone/RIGHT_ENC_A_RAW': 'J83.3 R802.1 R806.2',
    '/Rear zone/RIGHT_ENC_B_IN': 'R803.2 U81.9',
    '/Rear zone/RIGHT_ENC_B_RAW': 'J83.4 R803.1 R807.2',
    '/Rear zone/RIGHT_FILTER': 'C7.1 U3.6',
    '/Rear zone/RIGHT_RAW': 'J3.1 R6.1 U3.7',
    '/Rear zone/RIGHT_SCALED': 'J3.2 R6.2 R7.1 R8.1',
    '/Rear zone/R_BOOT0': 'J600.2 R600.1 U60.60',
    '/Rear zone/R_DEG_A_LED_ANODE': 'D612.2 R612.2',
    '/Rear zone/R_DEG_B_LED_ANODE': 'D613.2 R613.2',
    '/Rear zone/R_ERROR_LED_ANODE': 'D611.2 R611.2',
    '/Rear zone/R_LEFT_ENABLE_PWM': 'J603.10 R630.1 U60.42 U80.6',
    '/Rear zone/R_LEFT_ENC_A': 'J605.3 U60.28 U81.2',
    '/Rear zone/R_LEFT_ENC_B': 'J605.4 U60.55 U81.4',
    '/Rear zone/R_LEFT_IN1': 'R632.1 U60.34 U80.5',
    '/Rear zone/R_PWM_SET_MARKER': 'J603.9 U60.62',
    '/Rear zone/R_REAR_LEFT_LED_BASE': 'Q650.1 R650.2 R660.1',
    '/Rear zone/R_REAR_LEFT_LED_PLUS': 'J650.1 R670.2',
    '/Rear zone/R_REAR_LEFT_LED_SINK': 'J650.2 Q650.3',
    '/Rear zone/R_REAR_RIGHT_LED_BASE': 'Q651.1 R651.2 R661.1',
    '/Rear zone/R_REAR_RIGHT_LED_PLUS': 'J651.1 R671.2',
    '/Rear zone/R_REAR_RIGHT_LED_SINK': 'J651.2 Q651.3',
    '/Rear zone/R_RIGHT_ENABLE_PWM': 'J604.8 R631.1 U60.59 U80.11',
    '/Rear zone/R_RIGHT_ENC_B': 'J605.6 U60.33 U81.8',
    '/Rear zone/R_RIGHT_IN4': 'R635.1 U60.51 U80.12',
    '/Rear zone/R_SELFTEST_BUTTON': 'C610.1 J604.3 R602.2 SW61.1 U60.2',
    '/Rear zone/R_STATUS_LED_ANODE': 'D610.2 R610.2',
    '/Rear zone/R_SWCLK': 'J601.2 U60.49',
    '/Rear zone/R_SWDIO': 'J601.4 U60.46',
    '/Rear zone/R_TX_B_MARKER': 'J603.6 U60.15',
}
for net, endpoints in signal_groups.items():
    members = [tuple(endpoint.split('.')) for endpoint in endpoints.split()]
    assert all(pads[m].GetNetname() == net for m in members), (net, members)
    check_group('signal', net, members)

# The two physical pads of each switch pole must both reach the local circuit.
for ref in ['SW50', 'SW51', 'SW60', 'SW61', 'SW70']:
    fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
    for pin in ['1', '2']:
        physical = [a for a in fp.Pads() if a.GetNumber() == pin]
        reachable(physical[0])
        if any(a.m_Uuid.AsString() not in physical_reachable_cache[physical[0].m_Uuid.AsString()] for a in physical):
            errors.append({'reference': ref, 'group': 'physical switch pads', 'pin': pin})

tracks = list(board.GetTracks())
vias = [t for t in tracks if t.Type() == p.PCB_VIA_T]
segments = [t for t in tracks if t.Type() == p.PCB_TRACE_T]
assert tracks and vias, 'No initial routing found'
assert len({t.m_Uuid.AsString() for t in tracks}) == len(tracks)
assert all(t.GetStart() != t.GetEnd() for t in segments)
clock_routes = []
for n in [10, 14, 20, 24, 30, 34]:
    for pin in ['8', '9']:
        net = pads[(f'U{n}', pin)].GetNetCode()
        copper = [t for t in tracks if t.GetNetCode() == net]
        top_only = all(t.Type() == p.PCB_TRACE_T and t.GetLayer() == p.F_Cu for t in copper)
        length = sum(p.ToMM(t.GetLength()) for t in copper if t.Type() == p.PCB_TRACE_T)
        clock_routes.append({'reference': f'U{n}', 'pin': pin,
                             'top_only_no_vias': top_only, 'total_branch_length_mm': round(length, 3)})
        if not top_only:
            errors.append({'reference': f'U{n}', 'group': 'clock layer', 'pin': pin})
report = {
    'status': 'PASS for checked copper connections only' if not errors else 'FAIL',
    'fabrication_release': False,
    'errors': errors,
    'counts': {'track_segments': len(segments), 'through_vias': len(vias),
               'copper_zones': sum(not z.GetIsRuleArea() for z in board.Zones()),
               'full_unconnected_count': connectivity.GetUnconnectedCount(False)},
    'segment_width_counts_mm': dict(Counter(round(p.ToMM(t.GetWidth()), 3) for t in segments)),
    'via_diameter_drill_counts_mm': dict(Counter(
        f'{p.ToMM(v.GetWidth(p.F_Cu)):.2f}/{p.ToMM(v.GetDrill()):.2f}' for v in vias)),
    'checks': checks,
    'clock_routes': clock_routes,
    'backbone_nets': [
        {'net': net,
         'total_copper_length_mm_all_branches': round(sum(p.ToMM(t.GetLength()) for t in segments if t.GetNetname() == net), 3),
         'through_vias': sum(t.GetNetname() == net for t in vias)}
        for net in ['/CAN_A_H', '/CAN_A_L', '/CAN_B_H', '/CAN_B_L']],
    'remaining': [
        'Zone graph checks do not prove island continuity; native DRC unconnected items are authoritative.',
        'Regulator inputs and outputs still require board-wide distribution; two PG pull-ups await 3V3.',
        'High-current motor/servo paths and any failed signal groups remain pending; see Routing-review.md.',
        'Local CAN/MCU supply groups still need their board-wide 3V3 feed.',
        'CAN pair geometry, reference-plane continuity and signal-return paths need final review.',
        'Review Kelvin feedback returns, effective capacitance, loop geometry and thermal/current capability.',
        'Power-input, motor protection and heatsink decisions remain open; no fabrication release.'],
    'unfinished_signal_nets': ['/Front zone/F_DEG_A_LED', '/Front zone/F_DEG_B_LED', '/Front zone/F_FRONT_LEFT_LED', '/Front zone/F_FRONT_RIGHT_LED', '/Front zone/F_RX_A_MARKER', '/Front zone/F_RX_B_MARKER', '/Front zone/F_STATUS_LED', '/Front zone/F_STEER_TASK_MARKER', '/Front zone/F_TASK_PROBE', '/Front zone/F_TX_A_MARKER', '/Front zone/F_TX_B_MARKER', '/Front zone/F_UART_CONSOLE_RX', '/Front zone/F_UART_CONSOLE_TX', '/Rear zone/R_DEG_A_LED', '/Rear zone/R_DEG_B_LED', '/Rear zone/R_DIR_A_MARKER', '/Rear zone/R_ERROR_LED', '/Rear zone/R_LEFT_IN2', '/Rear zone/R_OVERLOAD_MARKER', '/Rear zone/R_PID_MARKER', '/Rear zone/R_REAR_LEFT_LED', '/Rear zone/R_REAR_RIGHT_LED', '/Rear zone/R_RELAY_TX_MARKER', '/Rear zone/R_RIGHT_ENC_A', '/Rear zone/R_RIGHT_IN3', '/Rear zone/R_RX_A_MARKER', '/Rear zone/R_RX_B_MARKER', '/Rear zone/R_STATUS_LED', '/Rear zone/R_STEER_TASK_MARKER', '/Rear zone/R_TASK_PROBE', '/Rear zone/R_TX_A_MARKER', '/Rear zone/R_UART_CONSOLE_RX', '/Rear zone/R_UART_CONSOLE_TX'],
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
}
args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'counts': report['counts'], 'errors': errors}, indent=2))
raise SystemExit(bool(errors))
