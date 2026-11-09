"""Optional bounded HTTPS mirror. submit() never performs networking or disk IO."""

from collections import deque
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlparse
import requests


class Uplink:
    def __init__(self, url, token, ack_path, session=None, start=True):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Use an HTTPS origin without embedded credentials, query or fragment"
            )
        if len(token) < 32:
            raise ValueError("Uplink token must have at least 32 characters")
        self.url, self.token = url.rstrip("/"), token
        self.ack_path = Path(ack_path)
        self.last_ack = (
            self.ack_path.read_text().strip() if self.ack_path.exists() else "0-0"
        )
        self.pending = deque(maxlen=1000)
        self.lock = threading.Lock()
        self.session = session or requests.Session()
        self.heartbeat = None
        self.last_heartbeat = 0
        self.dropped = 0
        self.last_error = None
        self.stop = threading.Event()
        self.thread = None
        if start:
            self.thread = threading.Thread(
                target=self._run, name="lab5-uplink", daemon=True
            )
            self.thread.start()

    def submit(self, row):
        with self.lock:
            if row["index"] <= int(self.last_ack.split("-")[0]):
                return
            if self.pending and row["index"] <= self.pending[-1]["index"]:
                return
            if len(self.pending) == 1000:
                self.dropped += 1
            self.pending.append(dict(row))

    def status(self, row):
        with self.lock:
            self.heartbeat = dict(row)

    def _post(self, endpoint, body):
        response = self.session.post(
            self.url + endpoint,
            json=body,
            headers={"Authorization": "Bearer " + self.token},
            timeout=(1, 2),
            allow_redirects=False,
        )
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise RuntimeError("Redirect refused; use the final HTTPS origin")
        return response.json()

    def once(self):
        with self.lock:
            row = dict(self.pending[0]) if self.pending else None
            hb = dict(self.heartbeat) if self.heartbeat else None
            count = len(self.pending)
        if row:
            result = self._post("/ingest/entry", row)
            expected = str(row["index"]) + "-0"
            if result.get("stream_id") != expected:
                raise RuntimeError("Unexpected acknowledgement")
            # Atomic local ACK replacement; a crash before this just retries the
            # idempotent Redis stream ID, never invents a successful upload.
            self.ack_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.ack_path.with_suffix(".tmp")
            tmp.write_text(expected, encoding="utf-8")
            tmp.replace(self.ack_path)
            with self.lock:
                self.last_ack = expected
                if self.pending and self.pending[0]["index"] == row["index"]:
                    self.pending.popleft()
        now = time.monotonic()
        if hb and now - self.last_heartbeat >= 1:
            hb.update(
                pending=count, last_ack=self.last_ack, uplink_dropped=self.dropped
            )
            self._post("/ingest/heartbeat", hb)
            self.last_heartbeat = now

    def _run(self):
        while not self.stop.is_set():
            try:
                self.once()
                self.last_error = None
                self.stop.wait(0.01)
            except Exception as exc:
                self.last_error = type(exc).__name__
                self.stop.wait(1)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=7)
        if not self.thread or not self.thread.is_alive():
            self.session.close()
