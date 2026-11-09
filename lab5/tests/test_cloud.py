import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cloud"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))
import fakeredis
from werkzeug.security import generate_password_hash
from app import create_app
from uplink import Uplink

TOKEN = "t" * 40


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.db = fakeredis.FakeRedis(decode_responses=True)
        self.app = create_app(
            self.db,
            dict(
                TESTING=True,
                USER="team",
                PASSWORD_HASH=generate_password_hash("test-only"),
                TOKEN=TOKEN,
            ),
        )
        self.client = self.app.test_client()
        self.auth = {"Authorization": "Bearer " + TOKEN}

    def entry(self, i=1):
        return dict(index=i, term=2, event=22, global_us=1000000 + i, replayed=True)

    def test_requires_login_and_distinct_uplink_auth(self):
        self.assertEqual(self.client.get("/api/state").status_code, 401)
        self.assertEqual(
            self.client.post("/ingest/entry", json=self.entry()).status_code, 401
        )
        basic = base64.b64encode(b"team:test-only").decode()
        r = self.client.get("/api/state", headers={"Authorization": "Basic " + basic})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json["stale"])

    def test_stream_retry_idempotency_conflict_and_gap(self):
        for _ in range(2):
            self.assertEqual(
                self.client.post(
                    "/ingest/entry", headers=self.auth, json=self.entry()
                ).status_code,
                200,
            )
        self.assertEqual(self.db.xlen("vehicle:log"), 1)
        bad = self.entry()
        bad["event"] = 23
        self.assertEqual(
            self.client.post("/ingest/entry", headers=self.auth, json=bad).status_code,
            409,
        )
        self.client.post("/ingest/entry", headers=self.auth, json=self.entry(4))
        self.assertEqual(self.db.get("vehicle:missing_entries"), "2")

    def test_heartbeat_ttl_and_last_snapshot(self):
        self.client.post("/ingest/heartbeat", headers=self.auth, json={"global_us": 42})
        self.assertGreater(self.db.ttl("vehicle:heartbeat"), 0)
        self.db.delete("vehicle:heartbeat")
        self.assertEqual(
            json.loads(self.db.get("vehicle:last_heartbeat"))["global_us"], 42
        )

    def test_uplink_retry_backlog_bound_and_ack_resume(self):
        client = self.client

        class Response:
            def __init__(self, response):
                self.response = response
                self.status_code = response.status_code

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(self.status_code)

            def json(self):
                return self.response.json

        class Session:
            fail = True

            def post(self, url, json, headers, **kwargs):
                if self.fail:
                    raise OSError("offline")
                return Response(
                    client.post(
                        "/ingest/" + url.rsplit("/", 1)[1], json=json, headers=headers
                    )
                )

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as d:
            session = Session()
            u = Uplink(
                "https://lab.invalid", TOKEN, Path(d) / "ack", session, start=False
            )
            for i in range(1, 1002):
                u.submit(self.entry(i))
            self.assertEqual(len(u.pending), 1000)
            self.assertEqual(u.dropped, 1)
            with self.assertRaises(OSError):
                u.once()
            self.assertEqual(len(u.pending), 1000)
            session.fail = False
            u.once()
            self.assertEqual(u.last_ack, "2-0")
            restarted = Uplink(
                "https://lab.invalid", TOKEN, Path(d) / "ack", session, start=False
            )
            restarted.submit(self.entry(2))
            restarted.submit(self.entry(3))
            self.assertEqual(len(restarted.pending), 1)
            restarted.once()
            self.assertEqual(restarted.last_ack, "3-0")
            u.close()
            restarted.close()
