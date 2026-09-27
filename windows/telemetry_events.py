"""Translate telemetry transitions into events, leaving continuous samples to the chart."""
from dataclasses import dataclass
from pi.part2_protocol import CURRENT_REPORT_MAX_MA, STATES

CATEGORIES = ('Connection', 'Buttons', 'Steering', 'Pedals', 'Sensor status', 'Errors', 'Diagnostics')
CHANNELS = ('left', 'right', 'servo')


@dataclass(frozen=True)
class LogEvent:
    category: str
    text: str


# Observe accepted frames; changing timestamps, counters and ordinary ADC noise are not events.
class TelemetryEvents:
    def __init__(self, connected_channels=CHANNELS):
        self.connected_channels = tuple(name for name in CHANNELS if name in connected_channels)
        self.connected = False
        self.state = None
        self.sensors = None

    def stale(self):
        if not self.connected:
            return []
        self.connected = False
        self.state = self.sensors = None
        return [LogEvent('Errors', 'Telemetry stale: no fresh status for 500 ms')]

    def receive(self, status):
        events = []
        if not self.connected:
            events.append(LogEvent('Connection', 'Telemetry received from Pi'))
            self.connected = True
        state = status['state']
        if state != self.state:
            name = STATES[state] if 0 <= state < len(STATES) else f'UNKNOWN({state})'
            events.append(LogEvent('Errors' if name.startswith('ERROR') else 'Connection', 'MCU state: ' + name))
            self.state = state
        sensors = tuple('unavailable' if not status['current_valid_mask'] & (1 << i)
                        or status[f'current_{name}_mA'] == -2147483648
                        else 'ceiling' if status[f'current_{name}_mA'] >= CURRENT_REPORT_MAX_MA
                        else 'available' for i, name in enumerate(CHANNELS)
                        if name in self.connected_channels)
        if sensors != self.sensors:
            text = '; '.join(f'{name}: {value}' for name, value in zip(self.connected_channels, sensors))
            events.append(LogEvent('Sensor status', text))
            self.sensors = sensors
        return events
