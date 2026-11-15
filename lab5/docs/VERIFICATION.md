# Offline verification — November 9, 2026

This records software/build checks, not a completed checkoff. Initial bring-up
and later hardware results are in `BRINGUP_2026-11-10.md`; remaining physical
cases are tracked in `CHECKOFF.md`.

**November 10 follow-up:** all **111 host tests pass**. The shared C library
and both firmware profiles build. Current offline images use N2 119900 bytes
flash / 60064 bytes RAM and N3 125540 / 62752. The new bounded Pi transmit retry
and health/input diagnostics are **not deployed or hardware-tested**. The last
hardware firmware/Pi revision is `107269a`, with Windows launcher `b693c57`.
At that baseline, complete saved histories agree through 3566 and both
N2-led/Pi-led functional routes worked; brief transition errors remain open.
See the [hazard review](HAZARD_REVIEW.md) for evidence, new checks and limits.
The table and image sizes below retain the dated November 9 baseline.

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

## November 9 hardware gates — historical baseline

Initial bring-up, selected functional cases and history comparisons have
since been completed. Use [CHECKOFF.md](CHECKOFF.md) for current status; the
list below records what had not been tested on November 9.

- First boot, physical CAN bus labels, new GPIO allocations, Pi native-library build, and GPIO/SocketCAN integration.
- Scope evidence for the 1 ms LED skew, 100 µs handover, 100 ms brake/error response and 1 s leader recovery limits; measured transfer delay, PPS jitter and drift.
- Flash erase/programming and Pi durable-write timing under load, watchdog behavior, stack usage, queue/controller overruns and recovery after actual power interruption.
- All ten live checkoff cases and all three physical failure scenarios, including persisted return/replay with the real wheel/proxy workload.
- Optional cloud deployment, TLS/hostname/login on a real VM, real Redis/container integration, and uplink-enabled/disabled timing comparison. Docker is unavailable on this host; the supplied container stack has not been started. Deployment was deferred by the team.

Builds and simulations cannot establish those physical results. Save captures and logs with the Git revision so any subsequent timing fixes can be evaluated against the same evidence.

## November 16 deployment of df259ad

All **111 host tests pass** at `df259ad`, and both firmware profiles build:
N2 120124 bytes flash / 61888 bytes RAM, N3 125756 / 64704. We updated the Pi
checkout and flashed both Nucleos with pyOCD under reset using sector erase.
Each flash erased sectors 0–4 only; the state region `0x08040000`–`0x0807ffff`
was read back before each flash and was not erased. ELF SHA-256: N2
`c24341a481e671d70d8e3b4fd60815789cf2db23094db72f8cd4d7ec9c993bdb`, N3
`eb9ce4ea72969917f450f6e5a39f4b7f5d38a6b3ceb68912853089bad9ffc476`.

Before the update, at `107269a`, one diagnostic event from each node committed
on all three (entries 3588–3590) and the full histories matched through 3590.
After the update and a Pi reboot, the Pi's boot service rejoined as follower
and all three full histories match through **3692** with no conflicts. Wheel
input was absent throughout, so every node stayed in ERROR with 2 Hz hazards.
No link cuts, power-off cases or scope measurements were made.

**Clock problem found with the new DRIFT output.** A node that became leader
kept the rate it last estimated as a follower. After the N2 flash the Pi led
term 529 with its rate frozen at 1.002477470. Followers slew at most 50 µs per
20 ms REF, about 2500 ppm, so they could not keep up: N2 and N3 `phase_err_us`
grew from about 20 ms to over 80 ms in about 90 seconds and was still rising.
The follower estimate came from single 20 ms REF intervals, where arrival
jitter of hundreds of microseconds reads as thousands of ppm, and its ±1%
filter biased the result toward 1.0. The Pi's raw clock also runs about
2100–2450 ppm faster than either Nucleo's; we have not found the cause, and it
is why the frozen error exceeded the slew. This code was unchanged since
`107269a`. The fix is recorded in the next section.

N3's console reports CAN state 2 (error-passive at the last state change) on
both buses since its flash, while its transmissions complete and all six links
are up. Transmit rejections continue on both Nucleos at roughly 1–3% of frames.
Neither is resolved. Evidence is in the ignored
`logs/lab5/20261116-agent-check/` and `logs/lab5/20261116-flash-df259ad/`.

## November 16 clock fix

Two changes in `core/clock.c`, with two new regressions in `test_core.py`;
all **113 host tests pass**:

- A new leader continues global time from its current reading and then runs
  at its own raw rate (rate 1.0) instead of its last follower estimate.
- A follower measures the frequency ratio across a baseline of 1 s growing to
  between 8 and 16 s, updated on every REF, instead of one 20 ms interval.

The fix is on all three nodes: both Nucleos were flashed (N2 120156 bytes
flash / 61952 RAM, N3 125788 / 64704; state region preserved as before) and
the Pi's `liblab5.so` was rebuilt from the same sources. ELF SHA-256: N2
`dbcb65e477397586667804951bea3164f5fe85758019793196acc9bab3f289f7`, N3
`3a1ba82f029c926fe80ea03c42403f90492fe0cec68593420a811a8d8bf11379`.

| Leader | Follower | Rate estimate (ppm) | Per-REF `phase_err_us` |
|---|---|---|---|
| N3, term 537, 40 s | N2 | −222 to +9 | −752 to +973, mean +56 |
| N3, term 537, 40 s | Pi | −2627 to −2007 | −3372 to +649, mean −28 |
| Pi, term 538, 60 s | N2 | +1537 to +2449 | −4538 to +1964, mean −488 |
| Pi, term 538, 60 s | N3 | +1660 to +2355 | −4198 to +1880, mean −541 |

Both leaders reported rate 1.0. With the Pi leading, follower error stayed
bounded for the whole capture, where it previously grew without limit.
`phase_err_us` is the difference between one arriving REF and the follower's
prediction, so its spread is mostly REF arrival jitter, several milliseconds
from the Pi. It is not the front/rear LED skew; that still needs the scope. In
simulation with comparable jitter, skew between two followers fell from about
1.1 ms to 0.16 ms at the 99th percentile. A leader's own `phase_err_us` is the
stale value from when it last followed. Evidence is in the ignored
`logs/lab5/20261116-clockfix/`.
