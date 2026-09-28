"""CSV and stdout are lower-priority observations, never UART producers."""
import csv
import sys
from pathlib import Path
from background_io import BackgroundIO
from part2_protocol import STATES, CURRENT_REPORT_MAX_MA


def current_summary(status):
    values = []
    for i, name in enumerate(('left', 'right', 'servo')):
        value = status['current_' + name + '_mA']
        valid = status['current_valid_mask'] & (1 << i) and value != -2147483648
        text = str(value) + 'mA' if valid else 'UNAVAILABLE'
        if valid and value == CURRENT_REPORT_MAX_MA:
            text += '[CEILING]'
        values.append('%s=%s' % (name, text))
    return ' '.join(values)


class BridgeDiagnostics:
    def __init__(self, path=None):
        self.file = self.writer = None
        if path:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.file = path.open('x', newline='')
        self.io = BackgroundIO(self._consume, self._finish)

    def message(self, text):
        self.io.submit(('message', text))

    def status(self, status, display):
        # The caller may reuse its dictionary after enqueueing.
        row = dict(status, diagnostic_records_dropped=self.io.dropped)
        self.io.submit(('status', (row, display)))

    def _consume(self, item):
        kind, value = item
        if kind == 'message':
            print(value, flush=True)
            return
        status, display = value
        if self.file:
            if self.writer is None:
                self.writer = csv.DictWriter(self.file, fieldnames=list(status))
                self.writer.writeheader()
            self.writer.writerow(status)
            self.file.flush()
        if display:
            mode = status['state']
            name = STATES[mode] if 0 <= mode < len(STATES) else 'UNKNOWN'
            print('STM %s steer=%d thr=%d brk=%d status_seq=%d dt=%sms rejected=%d %s' %
                  (name, status['steer'], status['throttle'], status['brake'],
                   status['status_seq'], status['stm_interval_ms'], status['rejected'],
                   current_summary(status)), flush=True)

    def _finish(self):
        if self.file:
            self.file.close()

    def close(self):
        stopped = self.io.close()
        # Command UART is already closed before this shutdown report.
        if self.io.error or self.io.dropped or not stopped:
            print('Diagnostic log incomplete: dropped=%d error=%s writer_stopped=%s' %
                  (self.io.dropped, self.io.error, stopped), file=sys.stderr)
        return stopped
