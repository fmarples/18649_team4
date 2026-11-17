# Optional cloud mirror

Deployed November 17 on a team member's AWS VM, behind that host's nginx, with the Pi publishing to it (see "Current deployment" below). The hostname, dashboard login and uplink token are private: `.env` and `dashboard_login.txt` in this folder are gitignored.

`app.py` is a nonvoting, read-only mirror. The Pi posts committed entries to an authenticated HTTPS endpoint. Entries use explicit Redis stream IDs `index-0`, making retries idempotent. Heartbeats use the `vehicle:heartbeat` hash with a five-second TTL. The last snapshot remains available with a staleness banner. A stream gap is reported if an outage exceeds the last-1,000-entry Pi queue.

The dashboard shows committed node/bus state, leader/time master, last reported held-event count, replayed entries, timestamps and uplink status. **While the Pi is off it cannot observe the Nucleos**: all these values are last known, and the banner says stale. A separate independently powered CAN-to-network gateway would be required to observe ongoing events during cockpit failure. The present Nucleo setup has no network uplink.

The Pi mirror worker performs HTTPS and ACK-file writes in its own thread. The control path only updates an in-memory queue/snapshot. On restart it reloads the last 1,000 durable display entries after the saved ACK. This is best-effort mirroring; Raft on the vehicle remains authoritative. The Pi has no input wired to the lamps, so it cannot measure the FL/RL offset itself. A scope reading can be supplied with `--offsets-json` (or `LAB5_OFFSETS_JSON`) as `{"fl_rl_offset_us": <FL edge time minus RL edge time>}`; the file is read once at start, so it adds nothing to the control path. An absent value stays null and shows “not measured.” It is not inferred from a desktop simulation.

## Local tests

Install `../requirements-host.txt` and run the main Lab 5 host suite. Tests use Flask's in-process client and a fake Redis store, including authentication, conflicting history, retry/ACK resume, queue bounding and heartbeat expiry. These tests do not prove a deployed TLS configuration or no added GPIO latency.

## Deployment inputs

A chosen VM/account, an HTTPS hostname pointing to that VM, and privately generated dashboard credentials/uplink token. The supplied Compose stack publishes only Caddy's ports 80/443; neither Redis nor the application exposes a host port. Redis runs on an internal network with AOF persistence. The Flask app trusts the included proxy's forwarded HTTPS header, so do not expose its port directly.

Before starting the stack, privately set `DOMAIN`, `DASHBOARD_USER`, `DASHBOARD_PASSWORD_HASH` (Werkzeug-generated hash) and a random `UPLINK_TOKEN` of at least 32 characters. A `.env` file is ignored; never commit real credentials. The Compose configuration refuses missing values. The app uses authenticated browser access and a separate bearer token for ingestion. Gunicorn serves the application; the Flask development server is not used. Caddy obtains HTTPS certificates for the supplied hostname.

After authorized deployment, the Pi option is `--cloud-url https://<hostname>` (or `LAB5_CLOUD_URL`) with `LAB5_UPLINK_TOKEN` supplied privately. The boot service reads both from `~/.config/team4-lab5/cloud.env` on the Pi (mode 600); without that file the cockpit runs with no uplink. TLS verification stays enabled; redirects are refused. Verify login, expiry/staleness, private Redis, retry after unplugging the uplink, and the one-time ordered replay. Capture GPIO/CAN timing with this feature enabled and disabled before claiming it never delays control.

### Host that already has a reverse proxy

When another web server holds ports 80/443, skip Caddy and add `compose.proxied.yaml`, which publishes the app on a loopback port (`APP_PORT` in `.env`):

```sh
docker compose -p team4-lab5 -f compose.yaml -f compose.proxied.yaml up -d --build redis app
```

The existing proxy must terminate HTTPS for the hostname and forward to that port with `X-Forwarded-Proto`. `DOMAIN` must still be set because `compose.yaml` requires it.

### After a pristine start

`lab5/pristine.py` removes the Pi's `cloud-ack.txt`, so the Pi republishes from index 1. The mirror still holds the old history and answers 409 (conflicting history) until its Redis data is cleared on the cloud host:

```sh
docker compose -p team4-lab5 exec redis redis-cli FLUSHDB
```

## Current deployment

November 17: Redis and the app run from `~/team4-lab5-cloud` on the VM as Compose project `team4-lab5`, using the proxied variant above on loopback port 8020 behind nginx with a Let's Encrypt certificate. Checked from outside the VM: HTTP redirects to HTTPS, a missing or wrong login returns 401, `/ingest/*` without the token returns 401, and ports 6379 and 8020 are closed. The Pi service was restarted with the uplink enabled; it uploaded entries 17740–18751 (the last 1,000 plus the restart's own) and the dashboard showed a current heartbeat with `pending` 0. The mirror reports a gap of 17,739 entries because it started after the history did.

The FL/RL offset on the dashboard is the November 18 direct scope reading with N3 leading term 644 (mean −250 µs, FL before RL; range −450 to 0), from `~/.config/team4-lab5/offsets.json` on the Pi. Update that file when a newer reading replaces it.

Not done yet: the scope capture with the uplink on and off, the uplink-unplug resume check, and the Pi power-cycle demonstration. The first restart with the uplink wrote one extra N1 down/up pair right after rejoining, while the 1,000-entry backlog was uploading; whether the upload caused it was not determined.

Sources: [Redis streams](https://redis.io/docs/latest/develop/data-types/streams/), [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/), [Caddy](https://caddyserver.com/docs/).
