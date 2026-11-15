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

**Step 1 needs empty stores and the Pi up first.** The default-leader boot applies only when a node's term and log are both empty (`core/lab5.c`, `l5_init`). With saved history, a power-up holds an election and any node can win. An empty Nucleo also elects within about 100 ms if it cannot hear the Pi, which then joins as a follower in term 2. `lab5/pristine.py` backs up and wipes all three stores and starts them in the right order; see the [README](../README.md#pristine-cold-start-erases-all-three-histories). It has not been run on the bench yet. Whether a wiped Nucleo should instead wait for its default leader is an open design choice.

For a pristine experiment, stop all nodes and back up their stores first. Firmware occupies sectors 0–5; only sectors 6–7 are Raft storage. Use the debugger's explicitly scoped erase operation after verifying the target and address range. Do not mass-erase during a normal rejoin test. The Pi's state directory contains both `raft.bin` and `display.sqlite`; retain these as a matched experiment history. No erase command is performed by the host test runner.

## November 16 step 2 capture (Pi-led, not a pristine start)

A 30 s `candump -L any` on the Pi at `6ba0316`, with the Pi leading persisted
term 538, wheel input present and all six links up. On each bus: REF from N1
1495 frames, mean 20.07 ms (4.8–36.9 ms), no missing cycle counters; empty
APPEND to N2 and to N3 mean 100.1 ms (94.8–105.4 ms); no REQ_VOTE and no
PREVOTE. CTRL, HB_N1/N2/N3, BLINK, FORCE, HELLO and REF were all present;
FAULT was absent, as expected with no fault. HB_N2 arrived 1370–1390 times and
HB_N3 about 1401 times per bus against 1500 for HB_N1; the shortfall is
unexplained. Intervals are Pi receive timestamps, not GPIO timing. Repeat after
the pristine cold start for the literal step 1 → step 2 sequence. Capture and
decoded CSV: ignored `logs/lab5/20261116-checkoff/step2-healthy-pi-led.*`.

## November 16 step 3 scope reading (Pi-led, left signal)

Scope CH1 on N2 FL (PA4), CH2 on N3 RL (PC4), delay CH1↑→CH2↑ with
statistics, as read off the screen by the user: **min −752 µs, max +618 µs,
|mean| under 10 µs**. Both extremes are inside the 1 ms limit; the edge count
and a photo were not recorded. The left command was held about 79 s; the Pi led
term 538 throughout and no election occurred.

The same recording shows two things that were not clean. N2's bus-A link
committed 142 DOWN/UP pairs in 186 s (entries 4026–4319; median outage 154 ms,
longest 6.5 s), with two pairs each for N1-A and N3-A, while the probes were
being attached and during the left-signal hold; it then stayed up. The cockpit
also committed 32 ERROR/OK pairs in short bursts when wheel UDP input paused,
each flashing hazards. Neither changed the term. Logs: ignored
`logs/lab5/20261116-checkoff/run1-step3-blinkers/`.

Hazards on the same probes, with the wheel GUI closed so every node was in
error at 2 Hz for about 156 s: **min −920 µs, max +708 µs, mean about −30 µs**
(user's reading; count and photo not recorded). All six links stayed up and the
term stayed 538. This is inside 1 ms by only 80 µs on the worst edge.

## November 16 step 4 attempt: failed, Pi bus-A link bad after reinsertion

Six pulls in the order N1-A, N1-B, N2-A, N2-B, N3-A, N3-B at Pi `6ba0316`,
starting from the Pi leading term 538. **Not a pass:** the term reached 564 and
3,775 entries were committed in about 7.5 minutes (4344–8118).

- The pulled link itself behaved: one DOWN entry each for N1-A, N2-A, N2-B,
  N3-A and N3-B, and one UP entry each for N2-A, N2-B and N3-B. N3-A bounced
  for 7 s on reinsertion (13 entries).
- After the N1-A jumper went back in, N1-A never settled: 3,284 DOWN/UP
  entries, about ten per second, down roughly half the time, and still flapping
  after the run. Over the run the Pi's bus-A transmit errors rose from 327 to
  36,516 and frames expired unsent from 1,080 to 240,703; bus B rose from 503
  to 2,378 and 505 to 6,765. Neither Nucleo reset.
- The other observations follow from that. Pulling N1-B isolated the Pi (N1
  DOWN, cockpit error, hazards, elections). With N2 off A, N3 had only the Pi
  left on A, so N3-A flapped 126 entries and its DEG_A lit; the mirror happened
  to N2-A (76 entries) with N3 off A. With N2 or N3 off B, that node depended
  on bus A and showed local hazards.
- New terms began at 134 s, 154 s and 160 s while the Pi still had bus B, then
  at 182–187 s (Pi isolated) and 324 s. The cause of the first three is not
  established; the entry storm delaying the Pi's heartbeats is a hypothesis.

User-reported LEDs: N1-A lit N1 DEG_A; N1-B turned hazards on; N2-A lit DEG_A
on N2 and N3; N2-B lit N2 DEG_B with FL/FR flashing; N3-A lit DEG_A on N2 and
N3; N3-B lit N3 DEG_B with the rear pair flashing. The core has no hold-off
before a link is declared UP again, so one bad contact writes entries without
bound; the log stops accepting entries at 30,000. Logs: ignored
`logs/lab5/20261116-checkoff/run2-step4-single-links/`.

## November 16 step 4 rerun after reseating the Pi's bus-A wires

Same six pulls, N2 leading term 564 (left over from the failed attempt), log
at 12,360 entries beforehand. **Term stayed 564 and N2 stayed leader.** The 76
entries 12361–12436 are identical in index, term and event on the Pi and on
both Nucleo consoles.

| Link | Pull | Reinsertion |
|---|---|---|
| N1-A | 1 DOWN | 17 entries over 4.5 s |
| N1-B | 1 DOWN | 15 entries over 5.3 s |
| N2-A | 1 DOWN | 11 entries over 3.8 s |
| N2-B | 1 DOWN | 5 entries over 0.9 s |
| N3-A | 1 DOWN | 1 UP |
| N3-B | 1 DOWN | 1 UP |

Every pull gave exactly one entry. Four of the six reinsertions gave several,
so "one MEMBER entry per change" holds for pulls but not for a jumper that
bounces going back in. The Pi's own DEG outputs followed its two pulls and no
cockpit error accompanied any pull; one unrelated burst of ten ERROR/OK pairs
occurred between pulls. The user confirmed the DEG LEDs lit only on the pulled
node and no blinkers flashed. Logs: ignored
`logs/lab5/20261116-checkoff/run2b-step4-single-links/`.

**Decision (user, November 16):** the extra reinsertion entries are contact
bounce from inserting a jumper by hand. Each bounce is a real link change and
the log records it correctly, so this is accepted behavior and no hold-off is
being added. For the demo, push each jumper home in one motion.

## November 16 step 9 first run: relay works, skew fails

N2 leading term 564; N2 pulled off B, then N3 off A, so N3 could reach the
leader only through the Pi. Held about nine minutes, then N3-A and N2-B
restored. **Term stayed 564**; each pull gave one DOWN entry, N3-A one UP and
N2-B 51 entries of reinsertion bounce.

- User's scope reading at N3: SYNC stayed high and REF_RX kept toggling.
- FL/RL delay while relayed: **min −4.73 ms, max −1.55 ms, mean −2.5 ms**, far
  outside 1 ms. After restoring both links: min −2.92 ms, max +0.74 ms, mean
  −0.9 ms; whether the scope statistics were reset first is not known, so this
  does not show a clean recovery.
- Cause, from the Pi's CAN capture: the Pi put each of N2's REFs on bus B a
  median 3.2 ms after receiving it on bus A (95th percentile 5.8 ms), but the
  relayed timestamp carried only a median 1.5 ms of correction. The shortfall,
  median 1.5 ms and up to 4 ms, matches the measured offset in size. The Pi
  dated a received frame when its notifier thread got to run, which can be
  milliseconds after arrival while the main loop holds the interpreter.

Pi fix (uncommitted; copied to the Pi checkout and the service restarted, no
Nucleo change): `Cockpit5.on_frame` dates a frame from SocketCAN's kernel
receive timestamp. In an idle process on the Pi that timestamp is a median
78 µs old at delivery. 119 host tests pass. Scope confirmation is pending.
Roughly every 300 s the wheel input pauses for about 2 s, giving about ten
COCKPIT_ERROR/OK pairs each time; the user attributes it to network lag. Logs:
ignored `logs/lab5/20261116-checkoff/run4-step9-stm32-master/`.

### Repeat after the kernel-timestamp change: not fixed, second cause found

User's scope readings (CH1 and CH2 were swapped against the plan, so a
negative delay means N3 behind N2): relayed through the Pi **−3.82 to
−1.58 ms, mean −2.1 ms**; all links restored, N2 still leading, statistics
reset first: **−1.39 to −0.48 ms, mean −0.89 ms**. Hazards came on part-way
through from a wheel-input pause.

- **Direct hop is under-corrected.** With no relay at all, N3 sat a mean
  0.89 ms behind the leader N2. Every node adds `can_delay_us` = 240 µs for a
  hop; `DESIGN.md` already calls that a planning value, not a measurement. The
  measured hop is therefore about 240 + 890 = 1130 µs. With the Pi leading
  both Nucleos are equally late, so the earlier Pi-led readings hid it.
- **The Pi's forwarding delay is not captured by its timestamp.** After the
  kernel-timestamp change the capture still shows the relayed stamp short by a
  median 1.3 ms (5th percentile 6.5–7.7 ms). The outbox stamps a REF just
  before `send()`; the frame then waits behind whatever is already in the
  interface's 10-frame queue.
- A follower filter that tracks the least-delayed REFs was simulated on the
  captured delays and still wandered about 0.8–1.0 ms, so it was not built.

Changes made (all **uncommitted**; 121 host tests pass):

- `config.json` `can_delay_us` 240 → **1130**, from the scope reading above.
  Both Nucleos rebuilt and flashed with pyOCD under reset and sector erase;
  each flash erased one 16 KiB firmware sector and left sectors 6–7 alone.
  **The pre-flash state backup failed on both boards** (the debugger read
  errored on N3; on N2 the target did not stay halted under reset) and the
  flash proceeded anyway, so there is no pre-flash image of either state
  region. Both boards rejoined at index 12863, matching the Pi. ELF SHA-256:
  N2 `e072ce61040e8fbef75575b2cc8ee2dfa03cc1e7113ee84ab263d0c4de568ed7`, N3
  `28d74ab231f4ba86b634bf737cd0464c6be4b96592be0cdca411049dc40a9efb`.
- Pi: REF frames (own and relayed) leave through a second send-only socket
  with `SO_PRIORITY` 6, which the interface's `pfifo_fast` queue sends ahead of
  ordinary frames; the looped-back copy is ignored on receive. With the Pi
  leading, the jitter between a REF's stamp and its send-complete time fell
  from about ±4.3 ms to ±2.0 ms (5th–95th percentile of the change between
  consecutive REFs, 20 s capture against the earlier step 2 capture).
- Pi: `sched_yield()` after sending a REF, so the CAN driver's worker can run
  at once. Its effect has **not been measured**.

Restarting the Pi while it led moved the term from 566 to 585. The Pi's log
of that restart shows the leader alternating between N2 and N3 on every term
from 581 to 585 with the commit index stuck at 12867; the cause is not
established and neither Nucleo console was being recorded. Evidence: ignored
`logs/lab5/20261116-checkoff/run4b-step9-after-pi-fix/` and
`flash-delay1130/`.

### Scope readings with `can_delay_us` 1130 and the Pi priority path

User's readings, same swapped channels, statistics reset before each:

| Topology | Min | Max | Mean | Before these changes |
|---|---|---|---|---|
| Direct, N2 leading, about 60 s of left signal | −1.21 ms | +1.21 ms | −0.14 ms | −1.39 / −0.48 / −0.89 ms |
| N2 off B and N3 off A (relay through the Pi) | −1.12 ms | −0.17 ms | −0.67 ms | −3.82 / −1.58 / −2.1 ms |

The means moved as intended, but **both still exceed 1 ms at an extreme**, and
the direct spread is wider than before. N3's console reported per-REF phase
errors from −1.7 ms to +1.0 ms during the direct reading, so N2's REF timing
itself jitters by more than a millisecond; N2 stamps a REF before `can_send`
may wait up to 2 ms for a free controller buffer.

The relayed reading is not clean: about 59 s into it the Pi stopped hearing
bus A for about 0.4 s (N1-A and N2 logged DOWN then UP), and the Pi became
leader in term 587, the only term change of the run. Whether the scope
statistics were read before or after that is not known. No kernel message
accompanied it. Logs: ignored `logs/lab5/20261116-checkoff/run6-delay1130-n2-led/`.

**Correction:** for these readings the Pi was still using `can_delay_us` 240;
only the Nucleos had 1130. `config.json` was copied to the Pi afterwards. The
relayed row therefore mixes a 240 µs relay stamp with an 1130 µs receive
correction and must be re-measured.

## November 16 steps 6 and 7 first run: power-off passes, return thrashes

Pi leading term 587, left signal on, Pi power pulled for about 50 s, then
restored. User saw fast hazards while the Pi was off and erratic hazards on
its return before they cleared.

- **Step 6 (power-off):** N2 became leader in term 588 in a single election
  and stayed leader for the whole outage. Console timestamps resolve only
  0.2 s, so the 1 s and 100 ms limits are not measured; no scope capture.
- **Step 7 (return):** terms 589–594 in three seconds, the leader alternating
  between N3 and N2. Fails "LEADER stays on the STM32".
- **Cause:** two places in `core/lab5.c` read the whole log in one call. Each
  node's HEALTH line showed its own report 270–310 ms old, so each stalled for
  that long with 13,000 entries, past the 60–99 ms election timeout:
  1. `rebuild_pending_graph` re-read entries 1..length after truncating a
     conflicting uncommitted suffix.
  2. `l5_held_events` re-read every entry up to the Pi's acknowledged index.
     A new leader starts that index at zero, so the Pi's first reply moved it
     across the whole log.
  The node that stalled missed heartbeats and stood for election; the next
  leader then stalled the same way. The first fix alone did not stop it.

Fixes (**uncommitted**; 123 host tests pass, three of them new regressions):

- `rebuild_pending_graph` starts from the applied graph and reads only the
  unapplied tail: 9 reads in the host test at 150, 600 and 1,500 entries.
- `l5_held_events` no longer reads the log. `apply()` remembers the indices of
  the last 32 user events; with more than 32 all still unacknowledged it
  reports the total.
- Firmware: a REF is re-stamped on every attempt while it waits for a free
  controller transmit buffer (previously stamped once, then up to 2 ms wait).

Both Nucleos reflashed twice with sector erase (sectors 0–4), each time after a
verified double read of sectors 6–7 saved to
`logs/lab5/20261116-checkoff/flash-rebuild-fix/` and `flash-held-fix/`. Final
ELF SHA-256: N2 `16ca3dd26c59fc025d55a430a522b2786d2197f12c2e6c1e51f437b734da30e4`,
N3 `54a88b2d23e414d91b16433f71d6c377109e448b8047ab3031f167210d1b4193`. The Pi has
the same core, `config.json` and `cockpit5.py` copied in and its library
rebuilt; its checkout is dirty against `6ba0316`.

Software check after the fixes (service restart, not a power pull): restarting
the Pi while it led term 605 gave one election (N2, term 606); restarting it
again as a follower left term 606 and N2 in place. The largest own-report age
in any Nucleo HEALTH line was 19 ms. **Still open:** for about four seconds
after the Pi returns, NODE_1 goes DOWN and UP about five times before it
settles, so hazards alternate during that time. Evidence: ignored
`logs/lab5/20261116-checkoff/run7-step6-7-pi-power/`,
`run8-pi-restart-after-fix/` and `run9-pi-restart-held-fix/`.

## November 16 wheel-input limit raised to 250 ms (user decision)

The user reported the left signal being interrupted by brief hazards often
enough to block other testing. The Pi's event logs for the night show 474
error entries, 427 of them with wheel input 100–120 ms old and nothing else
wrong; each cleared a median 40 ms later. After every gap of 80 ms or more,
three to six wheel packets arrived within 5 ms, so the packets were sent on
time and held on the Wi-Fi path. Turning the Pi's Wi-Fi power saving off
(`iw dev wlan0 set power_save off`, not persistent) did not reduce the gaps.
Of 651 gaps of at least 100 ms, 47 reached 150 ms, 11 reached 250 ms and 5
reached 500 ms; three of the longest were the proxy being closed on purpose.

**Decision:** the Lab 5 Pi fails N1 after 250 ms without a wheel update
instead of Lab 1's 100 ms (`UDP_FAIL_S` in `pi/vehicle/zone_state.py`, also
used by `cockpit5.py`). This is the user's explicit exception to "where the
lab sets a number, follow it exactly". The Lab 5 handout sets no proxy-loss
time; step 6's 100 ms limit concerns the Pi's CAN traffic and is unchanged;
`lab3_demo` keeps 100 ms. Cost: after a real proxy loss the last command is
held 250 ms before error. Uncommitted; 124 host tests pass. In the first 155 s
after deployment there were 11 gaps of at least 100 ms (largest 182 ms) and
no error entry.

Remaining report evidence: measured drift ratio/correction and PPS jitter, FL/RL skew, handover phase, failover/brake latency, equal committed logs/network snapshots for the three body scenarios, and any unpassed limits. The three technical discussion sections have one-page limits. All team members need to explain quorum, votes/terms, commit versus append, pre-vote, phase versus rate correction, and discovery versus committed routing.
