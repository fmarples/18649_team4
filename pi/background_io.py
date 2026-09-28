"""Bounded, best-effort diagnostics: slow sinks must never hold a command loop."""
import queue
import threading


class BackgroundIO:
    def __init__(self, consume, finish=lambda: None, capacity=1024):
        self.queue = queue.Queue(maxsize=capacity)
        self.consume, self.finish = consume, finish
        self.dropped = 0
        self.error = None
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._run, name='diagnostic-io', daemon=True)
        self.thread.start()

    def submit(self, item):
        if self.stopping.is_set() or self.error is not None:
            self.dropped += 1
            return False
        try:
            self.queue.put_nowait(item)
            return True
        except queue.Full:
            self.dropped += 1
            return False

    def _run(self):
        try:
            while not self.stopping.is_set() or not self.queue.empty():
                try:
                    item = self.queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                try:
                    self.consume(item)
                finally:
                    self.queue.task_done()
        except Exception as error:
            self.error = repr(error)
        finally:
            try:
                self.finish()
            except Exception as error:
                self.error = self.error or repr(error)

    def close(self, timeout=2):
        self.stopping.set()
        self.thread.join(timeout)
        return not self.thread.is_alive()
