"""Optional Pi 4 timing markers; libgpiod v2 is needed only with --trace-gpio.

BCM17/physical11 = each UDP datagram returned by recvfrom (before validation).
BCM27/physical13 = immediately before each UART write, including stop frames.
These are userspace markers, not NIC-arrival or physical UART-start timestamps.
"""
class NoTrace:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def udp_rx(self): pass
    def command_tx(self): pass


class GpioTrace(NoTrace):
    def __init__(self, chip):
        try:
            import gpiod
            from gpiod.line import Direction, Value
            self.Value = Value
            self.request = gpiod.request_lines(chip, consumer='lab2-timing', config={
                (17, 27): gpiod.LineSettings(direction=Direction.OUTPUT,
                                           output_value=Value.INACTIVE)})
        except (ImportError, AttributeError) as exc:
            raise RuntimeError('Timing GPIO needs libgpiod v2: install python3-libgpiod; use system python3.') from exc
        self.levels = {17: False, 27: False}

    def toggle(self, pin):
        level = not self.levels[pin]
        self.request.set_value(pin, self.Value.ACTIVE if level else self.Value.INACTIVE)
        self.levels[pin] = level

    def udp_rx(self): self.toggle(17)
    def command_tx(self): self.toggle(27)

    def __exit__(self, *args):
        try:
            self.request.set_values({17: self.Value.INACTIVE, 27: self.Value.INACTIVE})
        finally:
            self.request.release()


def create_trace(enabled=False, chip='/dev/gpiochip0'):
    return GpioTrace(chip) if enabled else NoTrace()
