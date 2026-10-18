"""Optional Raspberry Pi 4 timing probes using libgpiod v2.

BCM17 UDP_RX: toggled when recvfrom returns a datagram (userspace timestamp).
BCM27 CMD_TX: toggled immediately before the dual-CAN CTRL transmit group.
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
    def _toggle(self, pin):
        self.pins[pin] = not self.pins[pin]
        self.request.set_value(pin, self.Value.ACTIVE if self.pins[pin] else self.Value.INACTIVE)
    def udp_rx(self): self._toggle(17)
    def cmd_tx(self): self._toggle(27)
    def can_tx(self, bus): self._toggle(22 if bus == "can0" else 23)
    def __exit__(self, *args):
        try:
            self.request.set_values({pin:self.Value.INACTIVE for pin in self.pins})
        finally:
            self.request.release()

def create_trace(enabled=False, chip="/dev/gpiochip0"):
    return GpioTrace(chip) if enabled else NoTrace()
