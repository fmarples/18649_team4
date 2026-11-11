# Brief-hazard review — November 10, 2026

## Hardware-tested baseline

The last firmware and Pi revision run on the setup was
[`107269a`](https://github.com/fmarples/18649_team4/commit/107269a).
The final wheel/control and Pi-led two-cut tests also used the Windows launcher
from [`b693c57`](https://github.com/fmarples/18649_team4/commit/b693c57).
The firmware/Pi code in that later tree is unchanged from `107269a`, so
`b693c57` is the source snapshot for that tested combination.

**This version works for the functions tested on November 10:** normal
wheel/pedal controls, left/right/cancel, N2-led and Pi-led two-cut routing,
diagnostic-event delivery and matching saved histories through entry 3566.
In the Pi-led run, event 3418 reached all nodes.

Known limitations are separate from those completed results: brief errors
occurred during transitions, and scope limits plus remaining failure/replay
cases are still open. This is a working functional baseline, not a claim that
every Lab 5 requirement passed. See the [bring-up record](BRINGUP_2026-11-10.md).

The changes below passed software tests and firmware builds only. We have not
deployed them to the Pi or Nucleos. No running application, wiring or saved
history changed during this offline review.

## What the saved evidence establishes

N2 correctly drives the front pair and N3 the rear pair. While establishing
the Pi-B/N3-A cuts, N3 briefly reported ERROR while N2 remained OK. Each node's
local error override selects hazards independently. This explains the rear-only
flash; a shared clock cannot align outputs that have different modes. We have
not removed the local fault response to hide the symptom.

| Observation | Conclusion and limit |
|---|---|
| Before cuts, Pi input age reached 105.509 ms; the log has a 141.085 ms gap between accepted-update transmit records. Periodic control refresh and protocol work continued. | The Pi crossed the unchanged 100 ms input deadline. Saved data does not locate the delay between Windows transmission and Pi acceptance. Control sequence gaps include periodic refreshes and are not proof of missing UDP packets. |
| During cut establishment, ENOBUFS errors occurred on both the disconnected bus and still-connected Pi CAN A. Native decoding found complete N2 REPORT gaps up to 603.57 ms on A. | Full transmit buffers and delayed/missing reports can contribute to stale local health. Immediately discarding failed sends is a software weakness we can correct. Contact/controller effects and the original reason the queue filled are not fully resolved. |
| Settled route: 213.8 s of CAN traffic without ERROR heartbeats; normal controls worked. | The surviving route works once settled. This does not establish a fault-free transition or physical blinker skew. |

The Pi cannot observe the remote segment on its disconnected bus. Arrival
gaps are receiver observations, not precise source timing. Wall/monotonic
correlation has scheduling uncertainty. Raw evidence remains in the ignored
`logs/lab5/20261110-flash/pi-led-evidence/` directory and the serial/Windows
logs identified in the bring-up record.

## Offline correction and diagnostics

The Pi now keeps a separate bounded protocol transmit queue for each bus.
ENOBUFS means the operating system cannot accept another outgoing frame;
it does not mean that frame was delivered. We retry temporary failures
without sleeping or blocking the other bus. Each queue holds at most 128
frames and discards a software-queued frame at 20 ms of age. Retries are paced
at least 1 ms apart. This avoids immediately losing the remaining fragments
of a consensus message during a short burst while limiting stale backlog.
Raft acknowledgements and retransmissions still establish message delivery.

Local control messages keep their immediate path. Heartbeat, blinker and fault
work runs before queued protocol retries. REF timestamps include software
queue residence, recomputed from the original on each attempt. This cannot
recall frames already accepted into a kernel/controller queue or guarantee
delivery/timing. The 100 ms input timeout, 66 ms report-health threshold and
1 s watchdog are unchanged. Persistent state formats are unchanged.

| New record | Meaning |
|---|---|
| Pi can_tx_queue in STATUS/STATE_CAUSE | Per-bus pending, sent, temporary-full, expired, overflow and permanent-error counts. Interpret increases with the time interval and bus context. |
| Pi UDP_GAP | Accepted-input gap of at least 60 ms, actual UDP counter advance and receive timestamps. Rejected duplicates do not refresh the deadline. |
| Pi LOOP_SLOW | Slow outer-loop stages: socket waiting, input processing, tick and status work. Complements TICK_SLOW, which only covers the tick. |
| Nucleo HEALTH and Pi reason_mask | Local protocol-health cause and report ages; no printing inside the protocol lock. |

Health flags combine by addition: `1` paused, `2` Raft/storage failure,
`4` no fresh peer report, `8` Pi report missing/stale, `16` Pi-reported input
invalid. Report ages are ordered Pi/N2/N3 in milliseconds; `4294967295` means
unavailable. Application latches and missing controls remain separate fields.
RAFT_TX now records successful acceptance by SocketCAN, not a failed attempt
or proof of wire acknowledgement.

## Checks completed and remaining verification

All **111 host tests pass**, including a simulated ten-frame transmit buffer
that fills partway through a fragmented message, recovery through the real C
decoder, independent buses, queue expiry/capacity, retry pacing, REF correction,
unchanged stale-input rejection and health thresholds, and slow-loop logging.
The shared C library builds with warnings treated as errors. Both firmware
profiles build: N2 uses 119900 bytes flash / 60064 bytes RAM; N3 uses 125540 /
62752, within the 256 KiB firmware and 96 KiB RAM link regions. These are
linker totals, not measured stack peaks or execution-time bounds.

Persons 2 and 3 own the next hardware session, with AI supporting deployment
instructions and evidence analysis. Deploy matching code while preserving all
three histories. Make one focused capture of normal controls and the Pi-led surviving
route, including establishment/restoration. Combine Pi queue/error records,
both Nucleo HEALTH logs and CAN traffic. Record contact movement; do not repeat
every earlier single-link check solely for perfect insertion. Verify controls
and committed-log agreement, and determine whether local ERROR or stale-input
transitions recur. If they do, correlate the new reason/age records with an
Ethernet-arrival capture and sender timestamps. Person 1's assigned hardware
work is complete; this follow-up is handed to teammates for their planned
bench sessions. Persons 2 and 3 also cover the remaining scope, election,
persistence and rehearsal work. Report review and preparation to explain
the design remain shared; Person 1 does not need to operate later bench runs.

The saved captures do not justify declaring the brief-flash issue fixed yet.
