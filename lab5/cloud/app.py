"""Read-only vehicle mirror. Run behind HTTPS; Redis is private, never a voter."""

import hmac
import json
import os
import time
from pathlib import Path
from flask import Flask, abort, jsonify, request, Response
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import redis


def create_app(client=None, settings=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=65536,
        USER=os.getenv("DASHBOARD_USER"),
        PASSWORD_HASH=os.getenv("DASHBOARD_PASSWORD_HASH"),
        TOKEN=os.getenv("UPLINK_TOKEN"),
    )
    if settings:
        app.config.update(settings)
    if not all(app.config.get(k) for k in ("USER", "PASSWORD_HASH", "TOKEN")):
        raise RuntimeError(
            "Set dashboard user/password hash and uplink token; no default credentials"
        )
    if len(app.config["TOKEN"]) < 32:
        raise RuntimeError("UPLINK_TOKEN must have at least 32 characters")
    db = (
        client
        if client is not None
        else redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
            socket_timeout=2,
        )
    )
    # Only safe behind the included private Docker network / local reverse proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

    @app.before_request
    def auth():
        if not app.testing and not request.is_secure:
            abort(400, "HTTPS required")
        if request.path.startswith("/ingest/"):
            if not hmac.compare_digest(
                request.headers.get("Authorization", ""),
                "Bearer " + app.config["TOKEN"],
            ):
                abort(401)
        else:
            a = request.authorization
            if (
                not a
                or a.type != "basic"
                or not hmac.compare_digest(a.username or "", app.config["USER"])
                or not check_password_hash(
                    app.config["PASSWORD_HASH"], a.password or ""
                )
            ):
                return Response(
                    "Login required",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Team 4 Lab 5"'},
                )

    @app.after_request
    def security(response):
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'",
            }
        )
        return response

    @app.post("/ingest/entry")
    def entry():
        row = request.get_json()
        if not isinstance(row, dict) or any(
            type(row.get(k)) is not int for k in ("index", "term", "event", "global_us")
        ):
            abort(400)
        if (
            not 1 <= row["index"] <= 30000
            or not 1 <= row["term"] <= 65534
            or not 0 <= row["event"] <= 23
            or row["global_us"] < 0
        ):
            abort(400)
        sid = str(row["index"]) + "-0"
        data = {
            "term": row["term"],
            "index": row["index"],
            "type": (
                "EVENT"
                if row["event"] >= 21
                else "NOOP" if row["event"] == 0 else "MEMBER"
            ),
            "payload": json.dumps(
                {"event": row["event"], "replayed": bool(row.get("replayed"))}
            ),
            "global_time": row["global_us"],
        }
        for _ in range(8):
            try:
                with db.pipeline() as p:
                    p.watch("vehicle:last_index")
                    last = int(p.get("vehicle:last_index") or 0)
                    if row["index"] <= last:
                        old = p.xrange("vehicle:log", sid, sid)
                        if (
                            not old
                            or int(old[0][1]["term"]) != row["term"]
                            or json.loads(old[0][1]["payload"])["event"] != row["event"]
                        ):
                            abort(
                                409, "Conflicting history or missing acknowledged entry"
                            )
                        return jsonify(stream_id=sid, duplicate=True)
                    p.multi()
                    p.xadd("vehicle:log", data, id=sid)
                    p.set("vehicle:last_index", row["index"])
                    if row["index"] > last + 1:
                        p.incrby("vehicle:missing_entries", row["index"] - last - 1)
                    p.execute()
                    return jsonify(stream_id=sid, duplicate=False)
            except redis.WatchError:
                continue
        abort(503)

    @app.post("/ingest/heartbeat")
    def heartbeat():
        row = request.get_json()
        if not isinstance(row, dict):
            abort(400)
        row["received_wall"] = time.time()
        with db.pipeline(transaction=True) as p:
            p.hset(
                "vehicle:heartbeat", mapping={k: json.dumps(v) for k, v in row.items()}
            )
            p.expire("vehicle:heartbeat", 5)
            p.set("vehicle:last_heartbeat", json.dumps(row))
            p.execute()
        return jsonify(ok=True)

    @app.get("/api/state")
    def state():
        snapshot = json.loads(db.get("vehicle:last_heartbeat") or "{}")
        entries = [
            {"stream_id": sid, **row}
            for sid, row in reversed(db.xrevrange("vehicle:log", count=100))
        ]
        return jsonify(
            heartbeat=snapshot,
            stale=not bool(db.exists("vehicle:heartbeat")),
            entries=entries,
            missing_entries=int(db.get("vehicle:missing_entries") or 0),
        )

    @app.get("/")
    def index():
        return Response(
            (Path(__file__).with_name("index.html")).read_text(encoding="utf-8"),
            mimetype="text/html",
        )

    return app


if __name__ == "__main__":
    raise SystemExit("Use a production WSGI server behind HTTPS; see cloud/README.md")
