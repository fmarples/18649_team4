"""Optional Raspberry Pi 4 timing probes using libgpiod v2.

BCM17 UDP_RX: starts an edge pair at the first datagram in a drained batch.
BCM27 CMD_TX: matches that level immediately after CTRL is written to both buses.
Coalesced datagrams and stale command repeats do not introduce unmatched edges.
BCM22 CAN_TX_A and BCM23 CAN_TX_B: toggled before queueing each interface frame.
These are software-driven markers, not hardware NIC-arrival timestamps.
"""
class NoTrace:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def udp_rx(self): pass
    def cmd_tx(self): pass
    def can_tx(self, bus): pass

class GpioTrace(NoTrace):
    def __init__(self, chip="/dev/gpiochip0"):
        try:
            import gpiod
            from gpiod.line import Direction, Value
        except (ImportError, AttributeError) as exc:
            raise RuntimeError("GPIO trace requires libgpiod v2 (python3-libgpiod)") from exc
        self.Value = Value
        self.pins = {17:False, 27:False, 22:False, 23:False}
        self.request = gpiod.request_lines(chip, consumer="lab3-dual-can", config={
            tuple(self.pins): gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)})
    def _set(self, pin, active):
        if self.pins[pin] != active:
            self.request.set_value(pin, self.Value.ACTIVE if active else self.Value.INACTIVE)
            self.pins[pin] = active
    def _toggle(self, pin):
        self._set(pin, not self.pins[pin])
    def udp_rx(self): self._set(17, not self.pins[27])
    def cmd_tx(self): self._set(27, self.pins[17])
    def can_tx(self, bus): self._toggle(22 if bus == "can0" else 23)
    def __exit__(self, *args):
        try:
            self.request.set_values({pin:self.Value.INACTIVE for pin in self.pins})
        finally:
            self.request.release()

def create_trace(enabled=False, chip="/dev/gpiochip0"):
    return GpioTrace(chip) if enabled else NoTrace()
