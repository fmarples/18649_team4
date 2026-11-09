# Optional cloud mirror — prepared locally, not deployed

The team chose to prepare this extension locally and decide deployment later. No cloud resource or public endpoint has been created.

`app.py` is a nonvoting, read-only mirror. The Pi posts committed entries to an authenticated HTTPS endpoint. Entries use explicit Redis stream IDs `index-0`, making retries idempotent. Heartbeats use the `vehicle:heartbeat` hash with a five-second TTL. The last snapshot remains available with a staleness banner. A stream gap is reported if an outage exceeds the last-1,000-entry Pi queue.

The dashboard shows committed node/bus state, leader/time master, last reported held-event count, replayed entries, timestamps and uplink status. **While the Pi is off it cannot observe the Nucleos**: all these values are last known, and the banner says stale. A separate independently powered CAN-to-network gateway would be required to observe ongoing events during cockpit failure. The present Nucleo setup has no network uplink.

The Pi mirror worker performs HTTPS and ACK-file writes in its own thread. The control path only updates an in-memory queue/snapshot. On restart it reloads the last 1,000 durable display entries after the saved ACK. This is best-effort mirroring; Raft on the vehicle remains authoritative. Actual FL/RL measured offsets can be supplied with `--offsets-json`; absent values remain null and show “not measured.” They are not inferred from a desktop simulation.

## Local tests

Install `../requirements-host.txt` and run the main Lab 5 host suite. Tests use Flask's in-process client and a fake Redis store, including authentication, conflicting history, retry/ACK resume, queue bounding and heartbeat expiry. These tests do not prove a deployed TLS configuration or no added GPIO latency.

## Deployment inputs still needed

A chosen VM/account, an HTTPS hostname pointing to that VM, and privately generated dashboard credentials/uplink token. The supplied Compose stack publishes only Caddy's ports 80/443; neither Redis nor the application exposes a host port. Redis runs on an internal network with AOF persistence. The Flask app trusts the included proxy's forwarded HTTPS header, so do not expose its port directly.

Before starting the stack, privately set `DOMAIN`, `DASHBOARD_USER`, `DASHBOARD_PASSWORD_HASH` (Werkzeug-generated hash) and a random `UPLINK_TOKEN` of at least 32 characters. A `.env` file is ignored; never commit real credentials. The Compose configuration refuses missing values. The app uses authenticated browser access and a separate bearer token for ingestion. Gunicorn serves the application; the Flask development server is not used. Caddy obtains HTTPS certificates for the supplied hostname.

After authorized deployment, the Pi option is `--cloud-url https://<hostname>` with `LAB5_UPLINK_TOKEN` supplied privately. TLS verification stays enabled; redirects are refused. Verify login, expiry/staleness, private Redis, retry after unplugging the uplink, and the one-time ordered replay. Capture GPIO/CAN timing with this feature enabled and disabled before claiming it never delays control.

Sources: [Redis streams](https://redis.io/docs/latest/develop/data-types/streams/), [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/), [Caddy](https://caddyserver.com/docs/).
