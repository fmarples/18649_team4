"""Turn-signal selection, ported from the Lab 2 MCU's blinker_core.c.

N1 is the Lab 3 blinker master: it picks the mode here and transmits BLINK.
Paddles: bit 5 left, bit 4 right (Lab 2 wheel map). Pressing the active side
again, or both in one update, cancels; steering past the turn threshold and back
auto-cancels. Error forces hazard; leaving error returns to off.
"""
import can_protocol as p

LEFT_BUTTON = 1 << 5
RIGHT_BUTTON = 1 << 4
TURN_RAW = 8000
RETURN_RAW = 6000


class Blinker:
    def __init__(self):
        self.mode = p.BLINK_OFF
        self._previous = 0
        self._crossed = False
        self._recovering = False

    def _select(self, mode):
        self.mode = mode
        self._crossed = False

    def update(self, error: bool, buttons: int, steer: int) -> int:
        buttons &= LEFT_BUTTON | RIGHT_BUTTON
        pressed = buttons & ~self._previous
        self._previous = buttons
        if error:
            if self.mode != p.BLINK_HAZARD:
                self._select(p.BLINK_HAZARD)
            self._recovering = True
        elif self._recovering:
            self._select(p.BLINK_OFF)  # a held paddle on recovery is not a new request
            self._recovering = False
        else:
            if pressed == LEFT_BUTTON | RIGHT_BUTTON:
                self._select(p.BLINK_OFF)
            elif pressed & LEFT_BUTTON:
                self._select(p.BLINK_OFF if self.mode == p.BLINK_LEFT else p.BLINK_LEFT)
            elif pressed & RIGHT_BUTTON:
                self._select(p.BLINK_OFF if self.mode == p.BLINK_RIGHT else p.BLINK_RIGHT)
            if self.mode == p.BLINK_LEFT:
                self._crossed |= steer <= -TURN_RAW
                if self._crossed and steer >= -RETURN_RAW:
                    self._select(p.BLINK_OFF)
            elif self.mode == p.BLINK_RIGHT:
                self._crossed |= steer >= TURN_RAW
                if self._crossed and steer <= RETURN_RAW:
                    self._select(p.BLINK_OFF)
        return self.mode
