#!/usr/bin/env python3
"""Visual Part 3.4 bench sequence using the existing UART protocol.

Use firmware and part2_protocol.py from this same integration branch.
Stop part2_bridge.py and switch servo PWM OFF before running: this sequence
injects steering commands. It keeps throttle released and the brake pressed.
UART status checks do not prove that LEDs physically light or meet timing.
"""
import argparse
import time

import serial
from part2_protocol import STATES, command, pop_status

SELF_TEST_STATE = STATES.index('SELF_TEST')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='/dev/serial0')
    args = parser.parse_args()
    seq = 0
    buffer = bytearray()
    with serial.Serial(args.serial, 115200, timeout=0, write_timeout=0.2) as uart:
        # Let previous command sequences time out before starting at sequence 0.
        time.sleep(0.3)
        uart.reset_input_buffer()

        def segment(label, seconds, steer=0, buttons=0, transmit=True, expected_state=None):
            nonlocal seq
            print(label, flush=True)
            deadline = time.monotonic() + seconds
            next_tx = time.monotonic()
            observed_expected = False
            while time.monotonic() < deadline:
                now = time.monotonic()
                if transmit and now >= next_tx:
                    uart.write(command(seq, steer, 32767, -32768, buttons))
                    seq = (seq + 1) & 0xffffffff
                    next_tx = now + 0.02
                buffer.extend(uart.read(4096))
                for status in pop_status(buffer):
                    expected = expected_state if expected_state is not None else (1 if transmit else 2)
                    observed_expected |= status['state'] == expected
                time.sleep(0.001)
            if not observed_expected:
                raise RuntimeError('Expected STM link status was not received. Check UART and stop other bridge processes.')

        segment('1. Neutral/recovery: all four should be OFF.', 1)
        segment('2. Left paddle press: RED + YELLOW should start blinking.', .15, buttons=1 << 5)
        segment('   Keep watching the LEFT pair at 1 Hz.', 3)
        segment('3. Simulated left turn past threshold: left pair continues.', .8, steer=-12000)
        segment('   Return to center: all OFF (self-cancel).', 1)
        segment('4. Right paddle press: WHITE + BLUE should start blinking.', .15, buttons=1 << 4)
        segment('   Keep watching the RIGHT pair at 1 Hz.', 3)
        segment('5. Simulated right turn past threshold: right pair continues.', .8, steer=12000)
        segment('   Return to center: all OFF (self-cancel).', 1)
        segment('6. Select LEFT again.', .15, buttons=1 << 5)
        segment('   Left pair blinking.', 1.5)
        segment('   Select RIGHT: left stops immediately; right starts.', .15, buttons=1 << 4)
        segment('   Right pair blinking.', 1.5)
        segment('7. Both paddles: all OFF.', .15, buttons=(1 << 4) | (1 << 5))
        segment('   All OFF.', 1)
        segment('8. Stop UART commands: ALL FOUR should flash at 2 Hz.', 3, transmit=False)
        segment('9. Restore neutral UART commands: all OFF.', 1)
        segment('10. A single press: ALL FOUR hazards, even with a healthy link.', .15, buttons=1, expected_state=SELF_TEST_STATE)
        segment('    Release A: hazards stay latched.', 1, expected_state=SELF_TEST_STATE)
        segment('11. Double-press A: first press stays in hazards.', .08, buttons=1, expected_state=SELF_TEST_STATE)
        segment('    Release between presses.', .08, expected_state=SELF_TEST_STATE)
        segment('    Second press clears the self-test latch: all OFF.', .1, buttons=1)
        segment('    Neutral commands: all OFF.', 1)
        print('Sequence finished. UART checks passed; record what you SAW separately.', flush=True)
        print('Exiting stops commands, so timeout HAZARDS will resume. Start the live bridge next.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped. Command timeout should produce hazards.')
