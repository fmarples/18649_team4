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
    fields = {f.attrib['name']: (f.text or '') for f in c.findall('fields/field')}
    assert fields.get('MPN', '') == p['MPN'], f"MPN differs: {p['Reference']}"
assert sum(int(p['Qty_in_current_schematic']) for p in csv_rows('Preliminary-BOM.csv')) == len(parts)

# Assembly views must cover each schematic reference once, including unassigned
# footprints. Carrier alternatives belong in their own column, not the base MPN.
by_ref = {p['Reference']: p for p in parts}
for ref, mpn in [('R430','RT0603BRD0745K3L'),('R431','RT0603BRD0710KL')]:
    assert by_ref[ref]['MPN'] == mpn, (ref, '3.3V precision divider MPN')
    assert '0.1%' in by_ref[ref]['Value'], (ref, '3.3V divider tolerance')
for name in ['BOM-Hand-assembly.csv', 'BOM-JLC-hybrid.csv', 'Preliminary-BOM.csv']:
    seen = set()
    for row in csv_rows(name):
        if name == 'Preliminary-BOM.csv' and int(row['Qty_in_current_schematic']) == 0:
            continue
        refs = row['References'].split()
        quantity = row['Qty_in_current_schematic'] if name == 'Preliminary-BOM.csv' else row['Quantity']
        mpn = row['Part'] if name == 'Preliminary-BOM.csv' else row['MPN']
        assert len(refs) == int(quantity), (name, 'quantity', refs)
        for ref in refs:
            assert ref not in seen, (name, 'duplicate', ref)
            seen.add(ref)
            # The procurement view names generic headers even when the schematic
            # intentionally has no manufacturer-specific MPN for course headers.
            expected = by_ref[ref]['MPN']
            assert mpn == expected or (not expected and mpn == '2.54 mm breakaway header'), (name, ref, 'MPN')
            assert row['Footprint'] == by_ref[ref]['Footprint'], (name, ref, 'footprint')
    assert seen == set(by_ref), (name, 'reference coverage')

# TPS564252 DRL pin numbering and complete local support connectivity, checked
# against TI SLUSEQ6A pp. 3, 16-17, independently of generator metadata.
for i, prefix, output in [(0, 'P_SERVO', '/+6V6_SERVO'),
                          (1, 'P_5V', '/+5V'), (2, 'P_3V3', '/+3V3')]:
    u, base = f'U{40+i}', 410+10*i
    local = '/Power/' + prefix
    for pin, name in enumerate(['/VBAT_PROTECTED', local+'_SW', '/GND',
                                local+'_PG', local+'_EN', local+'_FB'], 1):
        expect(u, pin, name)
    expect(f'L{i+1}', 1, local+'_SW'); expect(f'L{i+1}', 2, output)
    # Only the regulator and inductor may touch the switching node.
    assert nets[local+'_SW'] == {(u, '2'), (f'L{i+1}', '1')}
    for offset, positive in [(0, '/VBAT_PROTECTED'), (1, '/VBAT_PROTECTED'),
                              (2, output), (3, output)]:
        expect(f'C{base+offset}', 1, positive)
        expect(f'C{base+offset}', 2, '/GND')
    for ref, first, second in [
        (f'R{base}', output, local+'_FB'), (f'R{base+1}', local+'_FB', '/GND'),
        (f'C{base+4}', output, local+'_FB'),
        (f'R{base+2}', '/VBAT_PROTECTED', local+'_EN'),
        (f'R{base+3}', local+'_EN', '/GND'),
        (f'R{base+4}', '/+3V3', local+'_PG')]:
        expect(ref, 1, first); expect(ref, 2, second)
    assert nets[local+'_FB'] == {(u, '6'), (f'R{base}', '2'),
                                (f'R{base+1}', '1'), (f'C{base+4}', '2')}
    for pin, name in enumerate([output, local+'_PG', '/GND'], 1):
        expect(f'J{42+i}', pin, name)

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
allowed = {'/+3V3', '/+5V', '/+6V6_SERVO', '/VBAT_PROTECTED', '/GND', '/CAN_A_H', '/CAN_A_L', '/CAN_B_H', '/CAN_B_L'}
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
for pin in [4]: expect('J70', pin, '/+5V')
for pin in [6, 9, 14, 20, 25, 30, 34]: expect('J70', pin, '/GND')
assert not any(('J70', str(pin)) in pin_net for pin in [1, 2, 39, 40]), 'Socket must omit Pi end pairs'
for pin in [17, 27, 28]:
    members = nets[pin_net[('J70', str(pin))]]
    assert members == {('J70', str(pin))}, f'Pi reserved pin must have its own no-connect: {pin}'

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

# Actuator integration checks (independent of generator metadata).
rear='/Rear zone/'; front='/Front zone/'
for pin,name in {1:'/GND',2:rear+'LEFT_BRIDGE',3:rear+'LEFT_RETURN',4:'/VBAT_PROTECTED',5:rear+'R_LEFT_IN1',6:rear+'R_LEFT_ENABLE_PWM',7:rear+'R_LEFT_IN2',8:'/GND',9:'/+5V',10:rear+'R_RIGHT_IN3',11:rear+'R_RIGHT_ENABLE_PWM',12:rear+'R_RIGHT_IN4',13:rear+'RIGHT_BRIDGE',14:rear+'RIGHT_RETURN',15:'/GND'}.items():expect('U80',pin,name)
for i,net in enumerate(['LEFT_BRIDGE','LEFT_RETURN','RIGHT_BRIDGE','RIGHT_RETURN']):
    expect(f'D{800+i*2}',1,'/VBAT_PROTECTED');expect(f'D{800+i*2}',2,rear+net)
    expect(f'D{801+i*2}',1,rear+net);expect(f'D{801+i*2}',2,'/GND')
for j,side in [(80,'LEFT'),(81,'RIGHT')]:
    expect(f'J{j}',1,rear+side+'_MOTOR');expect(f'J{j}',2,rear+side+'_RETURN')
for pin,net in [(1,'/GND'),(2,front+'SERVO_VPLUS'),(3,front+'SERVO_PWM_OUT')]:expect('J90',pin,net)
expect('U81',14,'/+3V3');expect('U81',7,'/GND')
for ref in ['J82','J83']:
    expect(ref,1,rear+'ENC_4V');expect(ref,2,'/GND')
for ref in ['R804','R805','R806','R807']:
    expect(ref,1,'/+3V3')
for pin,name in zip([2,4,6,8],['R_LEFT_ENC_A','R_LEFT_ENC_B','R_RIGHT_ENC_A','R_RIGHT_ENC_B']):expect('U81',pin,rear+name)
for pin in [11,13]:expect('U81',pin,'/GND')
for pin,net in {1:'/GND',2:'/+5V',3:rear+'ENC_4V'}.items():expect('U82',pin,net)
for ref,net in [('C804','/+5V'),('C805',rear+'ENC_4V')]:
    expect(ref,1,net);expect(ref,2,'/GND')
# Battery sense must be divided/filtered before reaching the ADC.
expect('R580',1,'/VBAT_PROTECTED')
for ref,pin in [('R580',2),('R581',1),('C580',1),('U50',17)]:expect(ref,pin,front+'BATTERY_ADC')
for ref in ['R581','C580']:expect(ref,2,'/GND')
assert nets[front+'BATTERY_ADC']=={('R580','2'),('R581','1'),('C580','1'),('U50','17')}
print('Actuator output, diode polarity, sensed current paths and encoder level-domain checks passed.')
missing = sorted(r for r, c in components.items() if not c.findtext('footprint'))
print(f'PASS: {len(components)} components; {len(nets)} nets; BOM, regulators, support circuits, interfaces, probe order and zone boundaries.')
print('Unassigned footprints: ' + (', '.join(missing) or 'none'))
print('These checks do not establish PCB completeness, ratings, physical fit, firmware operation or fabrication readiness.')
