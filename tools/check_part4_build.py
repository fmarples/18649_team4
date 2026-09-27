"""Check generated Kconfig/devicetree for the built image; no hardware is accessed."""
import argparse
from pathlib import Path
import pickle
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build/part4'))
    parser.add_argument('--zephyr-base', type=Path, required=True)
    args = parser.parse_args()
    config = (args.build / 'zephyr/.config').read_text()
    for item in ('CONFIG_MAIN_THREAD_PRIORITY=1', 'CONFIG_SYS_CLOCK_TICKS_PER_SEC=1000',
                 'CONFIG_LAB_TIMING_GPIO=y', 'CONFIG_LAB_CURRENT_SAMPLE_MS=20',
                 'CONFIG_LAB_CURRENT_MAX_AGE_MS=100', '# CONFIG_PRINTK_SYNC is not set',
                 'CONFIG_ADC=y'):
        if item not in config: raise SystemExit('FAIL: missing ' + item)
    sys.path.insert(0, str(args.zephyr_base / 'scripts/dts/python-devicetree/src'))
    # Read only the locally generated build artifact.
    with (args.build / 'zephyr/edt.pickle').open('rb') as f: tree = pickle.load(f)
    expected_pwm = [('left_pwm', 'pwm3', 1, 100000, 'tim3_ch1_pb4'),
                    ('right_pwm', 'pwm2', 3, 100000, 'tim2_ch3_pb10'),
                    ('steering_servo', 'pwm4', 4, 20000000, 'tim4_ch4_pb9')]
    for label, controller, channel, period, pin in expected_pwm:
        spec = tree.label2node[label].props['pwms'].val[0]
        ctrl = tree.label2node[controller]
        if spec.controller is not ctrl or ctrl.status != 'okay': raise SystemExit('FAIL: ' + label)
        if spec.data['channel'] != channel or spec.data['period'] != period: raise SystemExit('FAIL: period/channel ' + label)
        if pin not in ctrl.pinctrls[0].conf_nodes[0].labels: raise SystemExit('FAIL: pin ' + label)
        print('PASS:', label, controller, channel, period, pin)
    user = tree.get_node('/zephyr,user')
    for prop, port, pin in [('cmd-rx-gpios', 'gpioc', 2), ('pwm-set-gpios', 'gpioc', 3),
                          ('front-left-gpios', 'gpiob', 6), ('rear-left-gpios', 'gpioa', 4),
                          ('front-right-gpios', 'gpioa', 5), ('rear-right-gpios', 'gpiob', 8)]:
        spec = user.props[prop].val[0]
        if port not in spec.controller.labels or spec.data['pin'] != pin: raise SystemExit('FAIL: ' + prop)
        print('PASS:', prop, port, pin)
    adc = tree.label2node['adc1']
    if adc.status != 'okay' or adc.props['st,adc-prescaler'].val != 4:
        raise SystemExit('FAIL: ADC1 enable/clock')
    pins = {label for node in adc.pinctrls[0].conf_nodes for label in node.labels}
    if pins != {'adc1_in0_pa0', 'adc1_in1_pa1', 'adc1_in8_pb0'}:
        raise SystemExit('FAIL: current ADC pins')
    specs = user.props['io-channels'].val
    if [spec.data['input'] for spec in specs] != [0, 1, 8] or any(
            spec.controller is not adc for spec in specs):
        raise SystemExit('FAIL: current channel order')
    print('PASS: ADC1 PA0/PA1/PB0, channels 0/1/8, prescaler /4, reference mV:',
          adc.props['vref-mv'].val)
    print('PASS: generated configuration; physical waveforms still need measurement.')

if __name__ == '__main__': main()
