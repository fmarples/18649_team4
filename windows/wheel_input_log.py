"""Observe physical controls in the course proxy's existing DIJOYSTATE2 packets."""
import struct
from windows.telemetry_events import LogEvent

# Wrap only the existing outbound socket; never sample the SDK again or modify commands.
class InputLoggingSocket:
    def __init__(self, transport, log):
        self.transport, self.log = transport, log
        self.events = WheelInputEvents()

    def sendto(self, data, destination):
        for event in self.events.receive(data):
            self.log.record(event.text, event.category)
        return self.transport.sendto(data, destination)

    def reset(self):
        self.events.reset()

    def close(self):
        self.transport.close()


BUTTON_NAMES = {0: 'A / self-test (button 0)',
                4: 'Right paddle / right turn-signal request (button 4)',
                5: 'Left paddle / left turn-signal request (button 5)'}


# Compare observed input states; held buttons do not repeat on each wheel poll.
class WheelInputEvents:
    def __init__(self):
        self.reset()

    def reset(self):
        self.buttons = self.axes = self.povs = None

    def receive(self, data):
        if len(data) != 276:
            raise ValueError('Expected 276-byte course wheel packet')
        buttons = frozenset(i for i, value in enumerate(data[52:180]) if value & 128)
        events = []
        for index in sorted(buttons ^ (self.buttons or frozenset())):
            action = 'held on first sample' if self.buttons is None else 'pressed' if index in buttons else 'released'
            events.append(LogEvent('Buttons', f'{BUTTON_NAMES.get(index, "Button " + str(index))} {action}'))
        axes = struct.unpack_from('<8i', data, 4)
        for index, name, category in ((0, 'Wheel', 'Steering'), (1, 'Accelerator', 'Pedals'),
                                      (5, 'Brake', 'Pedals')):
            raw = axes[index]
            old = self.axes[index] if self.axes is not None else None
            if raw == old:
                continue
            if not -32768 <= raw <= 32767:
                raise ValueError(f'{name} axis outside signed calibrated range: {raw}')
            if index == 0:
                value = raw * 100 / (32768 if raw < 0 else 32767)
                position = 'centered' if raw == 0 else 'left' if raw < 0 else 'right'
                previous = old * 100 / (32768 if old < 0 else 32767) if old is not None else None
                amount = abs(value)
            else:
                value = (32767 - raw) * 100 / 65535
                position = 'released' if raw == 32767 else 'pressed'
                previous = (32767 - old) * 100 / 65535 if old is not None else None
                amount = value
            change = 'initial' if previous is None else f'change {value - previous:+.3f} percentage points'
            events.append(LogEvent(category, f'{name}: {position} {amount:.3f}%; {change}; raw={raw}'))
        # Preserve unmapped hardware axes instead of guessing which accessory is attached.
        for index, name in ((2, 'Axis lZ'), (3, 'Axis lRx'), (4, 'Axis lRy'),
                            (6, 'Slider 0'), (7, 'Slider 1')):
            old = self.axes[index] if self.axes is not None else None
            if axes[index] != old and (old is not None or axes[index] != 0):
                change = 'initial' if old is None else f'change {axes[index] - old:+d}'
                category = 'Pedals' if index >= 6 else 'Steering'
                events.append(LogEvent(category, f'{name}: raw={axes[index]}; {change} (unmapped SDK axis)'))
        povs = struct.unpack_from('<4I', data, 36)
        directions = {0: 'up', 4500: 'up-right', 9000: 'right', 13500: 'down-right',
                      18000: 'down', 22500: 'down-left', 27000: 'left', 31500: 'up-left'}
        for index, raw in enumerate(povs):
            old = self.povs[index] if self.povs is not None else None
            centered = raw & 0xffff == 0xffff
            if raw != old and (old is not None or not centered):
                position = 'centered' if centered else directions.get(raw, f'{raw / 100:.2f} degrees')
                events.append(LogEvent('Buttons', f'D-pad / POV {index}: {position}; raw={raw}'))
        self.buttons, self.axes, self.povs = buttons, axes, povs
        return events
