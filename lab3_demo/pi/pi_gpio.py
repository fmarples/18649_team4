"""N1 test points and LEDs on the Raspberry Pi 4 (libgpiod v2, BCM numbering).

Markers, probe-board rows 3-6: UDP_RX BCM17, CMD_TX BCM27, CAN_TX_A BCM22,
CAN_TX_B BCM23. UDP_RX starts an edge pair at the first datagram of a drained
batch; CMD_TX matches it right after the first CTRL write returns (student
clarification #1; the lab3_wcet_baseline bridge marks after both writes).
CAN_TX_A/B toggle on each write to that bus.

LEDs from doc/LAB3_PINOUT.md, active high through 470 ohm: DEG_A BCM5
(physical 29), DEG_B BCM6 (31), ERR BCM12 (32), ground on 39.
"""
UDP_RX, CMD_TX, CAN_TX_A, CAN_TX_B = 17, 27, 22, 23
DEG_A, DEG_B, ERR = 5, 6, 12
PINS = (UDP_RX, CMD_TX, CAN_TX_A, CAN_TX_B, DEG_A, DEG_B, ERR)


class NoGpio:
    """Stand-in for host tests and machines without the probe board."""
    def __init__(self):
        self.levels = {pin: False for pin in PINS}

    def _set(self, pin, active):
        if self.levels[pin] != active:
            self._write(pin, active)
            self.levels[pin] = active

    def _write(self, pin, active):
        pass

    def udp_rx(self):
        self._set(UDP_RX, not self.levels[CMD_TX])

    def cmd_tx(self):
        self._set(CMD_TX, self.levels[UDP_RX])

    def can_tx(self, bus):
        pin = CAN_TX_A if bus == 0 else CAN_TX_B
        self._set(pin, not self.levels[pin])

    def leds(self, deg_a, deg_b, err):
        for pin, on in ((DEG_A, deg_a), (DEG_B, deg_b), (ERR, err)):
            self._set(pin, on)

    def close(self):
        pass


class PiGpio(NoGpio):
    def __init__(self, chip="/dev/gpiochip0"):
        super().__init__()
        try:
            import gpiod
            from gpiod.line import Direction, Value
        except (ImportError, AttributeError) as exc:
            raise RuntimeError("Pi GPIO needs libgpiod v2 (python3-libgpiod); use --no-gpio to run without it") from exc
        self._value = Value
        self._request = gpiod.request_lines(chip, consumer="lab3-demo-n1", config={
            PINS: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)})

    def _write(self, pin, active):
        self._request.set_value(pin, self._value.ACTIVE if active else self._value.INACTIVE)

    def close(self):
        try:
            self._request.set_values({pin: self._value.INACTIVE for pin in PINS})
        finally:
            self._request.release()
