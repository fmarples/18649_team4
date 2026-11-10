# Offline verification — November 9, 2026

This records software/build checks, not vehicle measurements or a completed checkoff. The implementation is ready for initial bench bring-up. The physical cases in `CHECKOFF.md` remain pending.

**November 10 follow-up:** the suite now passes 72 tests and both updated
Nucleo builds were flashed. This page retains the November 9 baseline below;
see the [bring-up record](BRINGUP_2026-11-10.md) for fixes, current image sizes,
observations and unresolved hardware gates.

## Results

| Check | Result |
|---|---|
| Shared C core, Windows host library | Builds with Zig 0.14.1 C compiler, C11, `-Wall -Wextra -Werror` |
| Lab 5 host suite | 65 tests pass; no skipped tests |
| Existing Lab 3 Pi regression suite | 43 tests pass; original Lab 3 source unchanged |
| N2/front firmware | Zephyr 4.3.0 / SDK 0.17.4 build passes, `prj_n2.conf;swap_ab.conf` |
| N3/rear firmware | Same toolchain; `prj_n3.conf`, CAN swap disabled |
| Shared report layout | Exported and visually checked: three pages, one technical section per page |
| Must-do document | Exported and visually checked: three pages, remaining bench work first, completed offline integration work struck through at bottom |

Final N2 image uses **117,904 bytes flash / 52,768 bytes RAM**; N3 uses **123,552 bytes flash / 55,456 bytes RAM**. The link regions are 256 KiB firmware and 96 KiB RAM. The other 256 KiB of physical flash is reserved for the durable log. Linker totals include reserved thread stacks; they do not measure runtime stack high-water marks or worst-case latency. Assertions are enabled intentionally.

The host suite covers majority commit, votes/terms, stale candidates, conflicting/uncommitted suffixes, duplicate/lost messages, restart, pre-vote isolation, full 30,000-entry storage, interrupted bank switches, CAN fragmentation/CRC, two-bus routing, serialized bus traffic, source-event retries, held/replayed/live events, clock drift/wrap/handover and cold synchronization after multiple timestamp wraps. Pi tests use fake CAN/GPIO; they also verify REF compensation for work before transmission. SQLite tests check ordered display deduplication across restart. Cloud tests use Flask's test client and FakeRedis to check authentication, TTL/stale state, conflicting retries, bounded backlog and ACK resume. Analysis-tool tests reject empty/conflicting logs and missing scope edges.

The integration pass adds 18 single-link/leader combinations, 36 crossed two-link/cut-order/leader combinations, and all six single links in the serialized-bus model. It verifies one state entry per single-link transition, stable terms, equal committed graphs/logs, diagnostic event delivery, intact legacy relay traffic and malformed FAULT reporter rejection. The new saved-capture decoder is tested against production C fragments and synthetic network traffic; it validates both CRC layers and keeps bus reassembly separate. The read-only SQLite exporter and log comparison tests distinguish incomplete capture history from conflicting committed entries. See [integration review](INTEGRATION.md) for assertions and interpretation limits.

## Reproduce

From the repository root in the configured Python environment:

```sh
python lab5/host/build.py
python -m unittest discover -s lab5/tests -v
python -m unittest discover -s lab3_demo/pi -q
```

Install dependencies and build Nucleo profiles as described in `../README.md`. The GitHub workflow repeats the shared-core host checks on Linux; a local Windows pass is not a claim that a remote workflow ran.

## Still requires the actual setup

- First boot, physical CAN bus labels, new GPIO allocations, Pi native-library build, and GPIO/SocketCAN integration.
- Scope evidence for the 1 ms LED skew, 100 µs handover, 100 ms brake/error response and 1 s leader recovery limits; measured transfer delay, PPS jitter and drift.
- Flash erase/programming and Pi durable-write timing under load, watchdog behavior, stack usage, queue/controller overruns and recovery after actual power interruption.
- All ten live checkoff cases and all three physical failure scenarios, including persisted return/replay with the real wheel/proxy workload.
- Optional cloud deployment, TLS/hostname/login on a real VM, real Redis/container integration, and uplink-enabled/disabled timing comparison. Docker is unavailable on this host; the supplied container stack has not been started. Deployment was deferred by the team.

Builds and simulations cannot establish those physical results. Save captures and logs with the Git revision so any subsequent timing fixes can be evaluated against the same evidence.
