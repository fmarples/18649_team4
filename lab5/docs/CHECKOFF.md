# Lab 5 bench verification matrix

**The full TA checkoff remains unfinished.** The November 10 N2-led and Pi-led two-cut functional runs and restoration are recorded, and all three saved histories agree through entry 3566. N2/N3 single-link LED checks passed; Pi LEDs were reported correct. Steering/brake and both turn commands worked through the Pi-led route. Brief local errors during cut establishment, input/transport faults, remaining failure/replay cases and scope limits still need investigation or evidence. No extra single-link repeat is required solely for bounce-free jumper insertion; this does not turn an unperformed post-fix repeat into a pass. See [Pi-led evidence](BRINGUP_2026-11-10.md#pi-led-two-cut-route-controls-and-final-history-comparison). Host simulations do not complete the TA demo. Record revision/configuration, board IDs, bus labels, capture filenames and observed values. Preserve all three Raft stores on ordinary reboot/rejoin.

| Step | Action | Required observation / evidence |
|---|---|---|
| 1 | Pristine cluster, default cockpit leader, proxy off then on | Pi LEADER only; all SYNC; all error/hazards aligned before proxy; exit error after valid wheel input |
| 2 | Capture `candump -L any` | Catalog IDs; REF 20 ms with cycle/time; empty APPEND 100 ms; no election in default healthy mode |
| 3 | Left, right, cancel | Scope FL/RL/HZ; ≤1 ms skew over at least ten edges |
| 4 | Pull/recover each node's A and B separately | Lab 3 DEG behavior; unchanged term; one link-state/MEMBER entry per change at equal index on all nodes |
| 5 | N1 off B, N3 off A | Wheel/control still works; two link changes; no election; ≤1 ms skew; N2 diagnostic EVENT appears in N3 log via Pi |
| 6 | Power off Pi | Error/brake ≤100 ms; STM32 leader/REF ≤1 s; 4 Hz hazards; phase step ≤100 µs at handover |
| 7 | Return Pi without clearing its state | Pi remains follower; held events recorded once, ordered and marked replayed; later live events unmarked; hazards 2 Hz while error persists |
| 8 | Random leader mode with STM32-winning and Pi-winning seeds | Test both initial winners on actual boot order; STM32 failure alone does not force error; Pi failure does; replacement ≤1 s and replay works |
| 9 | STM32-led relayed-sync topology (handout scenario c) | Isolated-direct-path STM32 keeps SYNC/REF_RX, ≤1 ms skew; no edge jump after restore |
| 10 | Full node isolation and Lab 3 test-button sequence | Term unchanged for isolated follower, exactly one new term in healthy majority when leader isolated; verify outputs and clearing |

Before these: confirm new GPIO wiring from `PINS.md`; boot both images; inspect error, queue-drop and stack diagnostics. Verify fresh versus persistent startup intentionally. The default-leader bootstrap is only for fresh histories, not an instruction to delete logs whenever the Pi returns.

Latest Pi A/B evidence: all three histories agree on link DOWN/UP entries
2367–2370, with N2 remaining leader in term 519. A whole-Pi DOWN/UP transition
immediately after B reconnection has a reproduced receive-side cause: stale
B frames blocked current A reports in shared assembly state. The per-bus fix
passes host tests and capture replay and is deployed on all three nodes;
a standalone post-fix A/B repeat was deferred; subsequent two-cut runs
exercise routing and restoration but do not count as that exact repeat.
LEDs were tentatively reported correct. The separate display-replay fix is
deployed: entry 2201 was recovered and fresh complete histories agree across
all three nodes through 2434.
No extra repeat is requested solely for clean jumper insertion. The next
focused verification follows the [offline hazard correction](HAZARD_REVIEW.md),
which also identifies the last hardware-tested revisions.

Additional persistence check: preserve a log, reboot each node, and compare committed prefixes. Exercise conflicting uncommitted suffix recovery while scoping PPS and watching the watchdog. Host fault injection proves recovery ordering only under the modeled write boundary; real partial writes and flash stalls must be checked on the actual boards.

November 10 storage update: before the planned two-cut test, N3 entered an
erase/watchdog reset loop without an operator cut. The append-only repair
fix is deployed on Pi/N2/N3 at revision 107269a; all three saved histories
match through 3217, including the unchanged 2501-entry retained prefix.
The two-cut test had not started during that failure. The recovery comparison
does not sign off phase, election or physical power-loss timing.

The subsequent N2-led two-cut recording shows all nodes in graph `0x7/0x2d`
and one `EVENT_N2` at index 3230, term 524. Pi capture and all three full
3324-entry exports confirm delivery and agreement. All links were restored.
The brief hazard followed stale wheel input at 115.86 ms; the earlier Pi
down/up has no confirmed cause. A later Pi-led run completes the functional
route and controls portion of step 5, as detailed below.

For the Pi-led run, an intentional N2 reset elected N1 in term 525 without
clearing any state. With N1 off B and N3 off A, event 3418 traveled from N2
to Pi and then to N3 through N2. All three full histories match through 3566;
the team confirmed controls, turn signals and restored indicators. No further
election was observed during the cuts. Brief N3-only error heartbeats during
cut establishment explain how the rear pair could enter local hazards while
the front remained normal; the underlying transient cause is unresolved.
Extra graph entries also occurred, so this run does not establish exactly
two link-change entries for a clean two-cut transition. Scope skew and the
complete step-5 timing/transition criteria remain open. A settled 213.8-second
CAN interval had no error heartbeats; the overlapping 235.1-second application
interval had no state changes or accepted-input gaps of 100 ms or more.

Capture formats: scope rising edges `signal,time_s` CSV on one timebase; Nucleo serial text; Pi `events.csv`; `candump -L` text. Run `tools/analyze.py` for summaries. A capture of CAN arrival times cannot replace a GPIO phase measurement. A bounded modeled clock correction cannot replace the handover scope trace.

Integration evidence: use a separate named capture for the healthy baseline, each of the six single-link cut/restore runs, and the N1-off-B/N3-off-A bridge run. Record the cut/restore times, term, leader and committed graph before/after. Start the capture before pulling a jumper. On the Pi, its own disconnected interface cannot observe the remote segment; combine the capture with N2/N3 serial/network snapshots and endpoint behavior. A missing remote frame in the Pi capture alone does not prove failed relay. See [capture interpretation](INTEGRATION.md).

After traffic settles, use `lab5 log` on both Nucleos while idle and export the Pi's full durable history with `tools/export_ledger.py`. The per-run Pi CSV may omit earlier history after restart. Compare all three histories with `tools/analyze.py logs`; distinguish missing capture rows from conflicting values at the same index. Preserve the raw files even if a check fails.

For a pristine experiment, stop all nodes and back up their stores first. Firmware occupies sectors 0–5; only sectors 6–7 are Raft storage. Use the debugger's explicitly scoped erase operation after verifying the target and address range. Do not mass-erase during a normal rejoin test. The Pi's state directory contains both `raft.bin` and `display.sqlite`; retain these as a matched experiment history. No erase command is performed by the host test runner.

Remaining report evidence: measured drift ratio/correction and PPS jitter, FL/RL skew, handover phase, failover/brake latency, equal committed logs/network snapshots for the three body scenarios, and any unpassed limits. The three technical discussion sections have one-page limits. All team members need to explain quorum, votes/terms, commit versus append, pre-vote, phase versus rate correction, and discovery versus committed routing.
