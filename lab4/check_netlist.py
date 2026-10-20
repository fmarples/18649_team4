"""Check a KiCad XML export against the Lab 4 interface and support design.

Usage: python check_netlist.py exported-netlist.xml
This checks connectivity and BOM consistency, not physical or electrical ratings.
"""
from pathlib import Path
import csv
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
root = ET.parse(sys.argv[1]).getroot()
components = {c.attrib['ref']: c for c in root.findall('components/comp')}
nets = {}
pin_net = {}
for net in root.findall('nets/net'):
    name = net.attrib['name']
    members = {(n.attrib['ref'], n.attrib['pin']) for n in net.findall('node')}
    nets[name] = members
    for member in members:
        assert member not in pin_net, f'Pin on multiple nets: {member}'
        pin_net[member] = name

def csv_rows(name):
    with (BASE / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def expect(ref, pin, name):
    got = pin_net.get((ref, str(pin)))
    assert got == name, f'{ref}.{pin}: expected {name}, got {got}'

parts = csv_rows('KiCad/Circuit-BOM.csv')
assert len(parts) == len({p['Reference'] for p in parts})
assert {p['Reference'] for p in parts} == set(components), 'BOM references differ'
for p in parts:
    c = components[p['Reference']]
    assert c.findtext('value') == p['Value'], f"Value differs: {p['Reference']}"
    assert (c.findtext('footprint') or '') == p['Footprint'], f"Footprint differs: {p['Reference']}"
assert sum(int(p['Qty_in_current_schematic']) for p in csv_rows('Preliminary-BOM.csv')) == len(parts)

# Package-specific support checks independent of the generated connection metadata.
for zone, ref, prefix, hundred in [('Front', 'U50', 'F', 500), ('Rear', 'U60', 'R', 600)]:
    local = f'/{zone} zone/'
    for pin in [1, 19, 32, 48, 64]: expect(ref, pin, '/+3V3')
    for pin in [12, 18, 31, 47, 63]: expect(ref, pin, '/GND')
    expect(ref, 13, local + prefix + '_VDDA')
    expect(ref, 30, local + prefix + '_VCAP1')
    assert nets[local + prefix + '_VCAP1'] == {(ref, '30'), (f'C{hundred+6}', '1')}
    assert components[f'C{hundred+6}'].findtext('value') == '4.7u VCAP1'
    expect(f'C{hundred+6}', 2, '/GND')
    for offset in [0, 1, 2, 3, 4, 5]:
        expect(f'C{hundred+offset}', 1, '/+3V3')
        expect(f'C{hundred+offset}', 2, '/GND')
    expect(f'R{hundred}', 1, local + prefix + '_BOOT0')
    expect(f'R{hundred}', 2, '/GND')
    expect(f'R{hundred+1}', 1, '/+3V3')
    expect(f'R{hundred+1}', 2, local + prefix + '_RESET_N')
    for pin, name in enumerate(['/+3V3', local+prefix+'_SWCLK', '/GND', local+prefix+'_SWDIO', local+prefix+'_RESET_N', '/GND'], 1):
        expect(f'J{hundred+1}', pin, name)

for row in csv_rows('Interface-review.csv'):
    connection = row['Schematic_connection']
    if ' -> ' not in connection or ' / ' in connection or '/' in connection.split(' -> ')[0]: continue
    endpoint, name = connection.split(' -> ')
    ref, pin = endpoint.split('.')
    expected = '/' + name if name in ['+3V3', '+5V', 'GND'] else f"/{row['Zone']} zone/{name}"
    expect(ref, pin, expected)

# The two CAN backbones and power are the only allowed connections between sheets.
allowed = {'/+3V3', '/+5V', '/+6V6_SERVO', '/GND', '/CAN_A_H', '/CAN_A_L', '/CAN_B_H', '/CAN_B_L'}
for name, members in nets.items():
    sheets = {components[r].find('sheetpath').attrib['names'] for r, _ in members}
    assert len(sheets) < 2 or name in allowed, f'Unexpected cross-zone net: {name}'
for bus in ['A', 'B']:
    for wire, iso_pin, test_pin in [('H', 2, 3), ('L', 4, 4)]:
        name = f'/CAN_{bus}_{wire}'
        iso = [10, 20, 30] if bus == 'A' else [14, 24, 34]
        for number in iso:
            expect(f'J{number}', iso_pin, name)
            expect(f'J{number+1}', test_pin, name)
        assert not any(r.startswith('U') for r, _ in nets[name]), 'Transceiver bypasses isolation jumper'

# Pi supply isolation, ground pins and EEPROM reservations.
for pin in [2, 4]: expect('J70', pin, '/+5V')
for pin in [6, 9, 14, 20, 25, 30, 34, 39]: expect('J70', pin, '/GND')
for pin in [1, 17, 27, 28]:
    members = nets[pin_net[('J70', str(pin))]]
    assert all(r == 'J70' for r, _ in members), f'Pi reserved pin connected: {pin}'

# Lab 3 p17 specifies this physical probe-header order.
probe_common = ['GND', 'GND', 'RX_A_MARKER', 'RX_B_MARKER', 'TX_A_MARKER', 'TX_B_MARKER', 'DEG_A_LED', 'DEG_B_LED']
for zone, ref, prefix, tail in [
    ('Front', 'J503', 'F', ['SERVO_PWM', 'FRONT_LEFT_LED', 'FRONT_RIGHT_LED', 'RELAY_TX_MARKER', 'ERROR_LED']),
    ('Rear', 'J603', 'R', ['PWM_SET_MARKER', 'LEFT_ENABLE_PWM', 'DIR_A_MARKER', 'REAR_LEFT_LED', 'REAR_RIGHT_LED'])]:
    for pin, signal in enumerate(probe_common + tail, 1):
        expect(ref, pin, '/GND' if signal == 'GND' else f'/{zone} zone/{prefix}_{signal}')
for pin, signal in enumerate(['GND','GND','UDP_RX_MARKER','CMD_TX_MARKER','TX_A_MARKER','TX_B_MARKER','DEG_A_LED','DEG_B_LED'], 1):
    expect('J703', pin, '/GND' if signal == 'GND' else '/Cockpit zone/PI_'+signal)

for part in root.findall('libparts/libpart'):
    if part.attrib['part'] == 'MCP2515_TSSOP20':
        assert part.find("pins/pin[@num='17']").attrib['type'] == 'tri_state'

missing = sorted(r for r, c in components.items() if not c.findtext('footprint'))
print(f'PASS: {len(components)} components; {len(nets)} nets; BOM, support circuits, interfaces, probe order and zone boundaries.')
print('Unassigned footprints (still unresolved): ' + ', '.join(missing))
print('These checks do not establish PCB completeness, ratings, physical fit, firmware operation or fabrication readiness.')
