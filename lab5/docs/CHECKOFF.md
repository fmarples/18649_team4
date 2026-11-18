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

## November 18 restart after a full unplug and replug

After the user reconnected everything, the Pi's bus-A interface (`can0`) sat
in BUS-OFF with zero frames transmitted while it still received Nucleo
traffic; bus B was normal. N1's bus-A link flapped UP/DOWN into the log at
about 12 entries per second, taking it from about 13,800 to 17,843 entries
(N3 leading term 621). Stopping the Pi service stopped the growth. A few
minutes later, with no software change, `can0` transmitted test frames and
then the restarted service's traffic normally (ERROR-ACTIVE, no error frames
in 14 s, all six links up, log steady at 17,855). The user then reported the
cause: a broken bus-A connection, now repaired. With the wheel connected the
session reports READY (N3 leader, term 621, links 0x3f, no error). 12,145 entries remain before the 30,000
limit. ST-LINK ports are unchanged: N2 124020/COM6, N3 171333/COM4. Logs:
ignored `logs/lab5/20261116-checkoff/run12-after-replug/`.

## November 18 skew readings and the Pi's return (run 12)

N3 leading term 621, `can_delay_us` 1130, REF re-stamp and priority socket in
place. Scope: CH1 = N3 RL, CH2 = N2 FL, delay CH1↑→CH2↑, user-read.

| Path | Min | Max | Mean |
|---|---|---|---|
| Direct | −1.19 ms | +0.35 ms | reported as 0.39 ms; taken as −0.39 ms, since a mean above the maximum is impossible |
| Relayed through the Pi (N2 off B, N3 off A) | −1.04 ms | −0.27 ms | −0.60 ms |

Both exceed 1 ms at one end. The pulls and reinsertions wrote one entry each
(N2-B reinsertion three), term unchanged.

**Pi power cycle (step 7): failed.** Power-off wrote NODE_1_DOWN and
COCKPIT_ERROR and the hazards were fast and steady. After power-on, NODE_1
went UP 37 s later and then cycled DOWN/UP about 35 times over 30 s (entries
17,865–18,072, 210 entries, term 621 unchanged); the user saw erratic
blinkers until it settled. Cause, from the Pi's `events.csv`: the service
starts 12 s into boot with commit index 0 and replays all 17,862 entries in
about 7 s, with ticks up to 240 ms; ticks of up to 350 ms continued until
about 29 s while the rest of boot finished. Peers drop a node whose REPORT is
older than 66 ms, so each long tick wrote NODE_1_DOWN and the next REPORT
wrote it UP again. A service restart without a reboot gave 3 such cycles at
this log length. SD-card sync time on the quiet system is 3 ms median, so the
store's per-entry fsync is not the cause in steady state.

**Fix:** a restarted Pi stays quiet (no HELLO or REPORT, Raft traffic
unchanged) until it leads, or has a leader, has applied everything committed,
has no replay backlog, and has gone 1 s without two ticks 40 ms apart
(`ANNOUNCE_*` in `pi/cockpit5.py`; `quiet` flag in `core/agent.c`, never set
on the Nucleos). It logs `ANNOUNCE` once. Two new host tests; 126 pass. Two
service restarts with the fix each wrote exactly NODE_1_DOWN, COCKPIT_ERROR,
then NODE_1_UP, both links UP and COCKPIT_OK. **A power cycle with the fix is
not yet tested.**

**Calibration:** `can_delay_us` 1130 → 780, from the direct mean (follower
390 µs early) and half the relayed mean (300 µs per hop). Not yet measured.

Both Nucleos were reflashed with these changes (sector erase, histories
backed up first; all three nodes agree at index 18,114 afterwards). ELF SHA-256:
N2 `2a86d748…32b2af2`, N3 `c6f3ba15…52c1664d`. Halting N3 for its backup made
the Pi leader for term 623; restarting the Pi service gave N3 term 624. Each
Nucleo showed one extra DOWN/UP 0.1 s after its flash, which fits pyOCD
resetting twice; not investigated. Log at 18,114 entries. Uncommitted. Logs:
ignored `logs/lab5/20261116-checkoff/run12-after-replug/`,
`run13-announce-gate/`, `flash-announce-delay780/`.

## November 18 second round: delay 780 and the Pi's return (runs 14–16)

N3 leading term 624, `can_delay_us` 780. Same scope setup, user-read.

| Path | Min | Max | Mean |
|---|---|---|---|
| Direct | −1.62 ms | +0.54 ms | −0.25 ms |
| Relayed through the Pi | −0.15 ms | +0.68 ms | +0.23 ms |

**Relayed passes; direct fails at the minimum.** The relayed mean moved
+0.83 ms for the 350 µs change (two hops), the direct mean only +0.14 ms, and
the direct spread is 2.16 ms, so centring alone cannot bring direct inside
±1 ms. N2's own REF phase error in the direct window ran −1.67 to +0.38 ms
per 30 s. The cause of the negative tail is not established.

**Pi power cycle with the quiet start alone: still failed.** The Pi announced
20.3 s after boot with ticks under 51 ms, then ticks of 60–240 ms returned
for 17 s and NODE_1 cycled about 25 times (entries 18,121–18,268). Every long
tick was in CAN receive next to an entry being stored. Measured on the Pi:

- Store sync behind another disk writer: `fsync` up to 4.4 s (3.8 ms idle),
  `fdatasync` up to 7 ms in the same test. The store now uses `fdatasync`
  (`host/bridge.c`); its file has a fixed size and is overwritten in place.
- Under a CPU, login and 100 MB disk-write load, control-loop stalls of 30 ms
  or more: 15 (worst 2.9 s, 27 entries written) at normal priority; 0 and 2
  (worst 0.92 s, a store sync behind the disk write, 6 entries) at FIFO 1.
  The service unit now sets FIFO priority 1.

**Result: two `systemctl reboot` runs each wrote exactly NODE_1_DOWN,
COCKPIT_ERROR, then 34 s later NODE_1_UP, both links UP and COCKPIT_OK**
(entries 18,347–18,352 and 18,353–18,358, term 624 unchanged). After the
announcement the longest loop was 24.8 ms. A physical power cycle with these
fixes has not been observed by the user yet. Residual: a large disk write on
the Pi can still stall one store sync. The disk-load tests themselves wrote
about 60 flap entries. Log at 18,358 entries. Uncommitted; 126 host tests
pass. Logs: ignored `logs/lab5/20261116-checkoff/run14-delay780/`,
`run15-reboot-fifo/`, `run16-reboot-fifo/`.

## November 18 third round: lamp edges were late on the boards themselves

User: a physical Pi power cycle now returns with one clean switch. Direct
skew over about ten edges, N3 leading, delay 780: −1.22/+0.34 (mean −0.25)
and −1.05/+0.29 ms (mean reported as .168, sign not given). Both miss −1 ms.

Cause found with a new firmware counter (`BLINK_EDGE`, time from each lamp
phase boundary in the board's own global time to the thread seeing it). On
N3 before the fix: 24 of the first 33 edges were 500 µs or more late, window
maxima 0.76–2.16 ms. The blink thread ran at priority 2 and took `raft_lock`
three times per pass; CAN receive and Raft work hold that lock and run above
it (`rx_dispatch` maxima 3.6–3.8 ms on both boards).

**Fix (`stm32_zephyr/src/main.c`, `lab5_runtime.c`):** the blink thread runs
at priority 0, reads a copy of the clock and hazard rate under a spinlock
instead of `raft_lock`, and busy-waits the last 250 µs before each boundary.
After the fix, 30 s on each board: window maxima 47–349 µs, no edge at or
over 500 µs outside boot. `can_delay_us` stays 780 but was calibrated against
the late edges, so it must be re-measured. Flashed to both boards with
history backups (sector erase); ELF SHA-256 N2 `03050ad6…`, N3 `167b79b7…`.
The flashes moved leadership to the Pi (term 625); restarting the Pi service
gave N2 term 626 with one clean NODE_1 set. Log at 18,444. **Scope skew with
the fix is not yet measured.** Uncommitted; 126 host tests pass. Logs:
ignored `logs/lab5/20261116-checkoff/run17-next/`, `flash-blink-diag/`,
`flash-blink-fix/`.

## November 18 fourth round: skew after the blink fix (run 18)

N2 leading term 626, delay 780, about ten edges per reading, user-read.

| Path | Min | Max | Mean |
|---|---|---|---|
| Direct, try 1 | −0.56 ms | +0.32 ms | −0.03 ms |
| Direct, try 2 | −0.36 ms | +0.27 ms | −0.02 ms |
| Relayed through the Pi | −0.87 ms | −0.25 ms | −0.50 ms |

**All three are inside ±1 ms.** Direct needs no recalibration. The user also
confirmed a physical Pi power cycle returns with one clean switch. Over the
9 minutes, 5 (N2) and 3 (N3) lamp edges were 500 µs or more late out of
about 1,100 each. Pulls and reinsertions wrote one entry each.

The relayed offset is the Pi's send path. From the capture (3,398 relayed
REFs): kernel receive to transmit-complete averaged 3.01 ms; the stamp
credited 2.51 ms including the 780 µs hop, so the Pi takes about 1.28 ms from
`send()` to transmit-complete where a Nucleo hop is allowed 780 µs. **Fix
(Pi only):** `pi_ref_send_us` = 500 in `config.json`, added to every REF
stamp the Pi sends (`pi/can_outbox.py`); from the −0.50 ms scope mean. Not
compiled into the firmware. Deployed; one clean NODE_1 set on restart. **Not
yet measured.** 127 host tests pass. Uncommitted. Log at 18,454. Logs:
ignored `logs/lab5/20261116-checkoff/run18-blink-fix/`.

## November 18 fifth round: relayed skew with the Pi send allowance (run 19)

N2 leading term 626, relayed through the Pi (N2 off B, N3 off A), about ten
edges, user-read: **min −0.45 ms, max +0.17 ms, mean −0.17 ms.** With the
direct readings above, step 9's skew limit is met for an STM32 leader.

Open, seen once in four N2-B pulls today: 0.3 s after N2 left bus B, N3's
HELLO stopped on both buses for 0.13–0.24 s and NODE_3 then went DOWN/UP
five times over 2.3 s with link entries for N3 and N1-B (entries
18,456–18,485), before N3-A was pulled 3.3 s later. Term unchanged. N3
reported bus A receive-error-passive and bus B transmit-error-passive at the
time. Cause not established. Restores wrote one entry each.

On-board evidence for step 6's error limit: at each Pi loss both Nucleos log
`HEALTH reasons=0x8` with the Pi's report age at 66 ms.

Three leader resets (`pyocd reset`) then moved leadership N2 → N3 → N2 → Pi;
the Pi leads term 629, log at 18,519.

## November 18 Pi-led steps 3, 5, 6 and 7 (run 20)

Pi leading term 629. Scope as before, about ten edges, user-read.

| Step | Min | Max | Mean |
|---|---|---|---|
| 3, direct | −0.25 ms | +0.17 ms | −0.03 ms |
| 5, N1 off B and N3 off A (RL relayed through N2) | −0.67 ms | +0.22 ms | −0.16 ms |

- **Step 3:** passes; the user reports left, right and cancel as expected.
- **Step 5:** wheel control and lamps worked (user). No election: term 629
  throughout. `EVENT_N2`, requested on N2's console 12 s after both cuts were
  committed, is entry 18,534 in term 629 on both N2 and N3. **Not exactly two
  link entries:** N1-B pull wrote 7 alternating DOWN/UP entries over 2 s, N3-A
  pull 7 over 1–3 s, N3-A reinsertion 13 over 5 s, N1-B reinsertion 1. The
  decoded REPORT masks show the pulled interface really received HELLOs in
  60–70 ms windows during those intervals (the Pi's own frames were also
  ACKed on bus B), so this is intermittent contact, which the user has ruled
  correct behavior. A clean two-entry transition is still not on record.
- **Step 6:** both Nucleos logged `HEALTH reasons=0x8` at a Pi report age of
  66 ms. N3 was candidate and then leader of term 630 within one 0.2 s console
  interval of that line; one election. User: hazards fast and steady. Brake
  latency and the handover phase step were not scoped; N2's logged REF phase
  error shows no change across the handover, but its ±0.8 ms sample noise
  cannot resolve 100 µs.
- **Step 7:** the Pi returned as a follower of N3; entries 18,549–18,551 are
  marked replayed on the Pi and the later ones are not; one NODE_1 set.
  About 33 s later the Pi sent FAULT test-button and then FAULT clear 143 ms
  apart (wheel test button double press in the wheel packets), which wrote
  one more NODE_1 DOWN/UP set (18,556–18,561) as designed.

Log at 18,561; N3 leads term 630. Logs: ignored
`logs/lab5/20261116-checkoff/run20-pi-led-step3-5/`.

## November 18 step 10 and the N3 watchdog resets (runs 21–25)

N3 leading term 630 at the start. User-observed lamps, recorder logs.

| Action | Lamps (user) | Log |
|---|---|---|
| N2 isolated (both buses), restored | Front pair fast hazards, rear normal | Term 630 unchanged; NODE_2_DOWN, later UP; N2-B reinsertion wrote 21 alternating link entries over 9 s |
| N3 (leader) isolated, restored | Rear pair fast hazards, front normal | Exactly one new term (631); N3-B reinsertion wrote 13 link entries |
| N2 test button, then double press | Front fast hazards, rear slower; cleared | One new term (632; N2 had led 631); NODE_2_DOWN, COCKPIT_ERROR |
| N3 test button, then double press | Rear fast, front slower; cleared | COCKPIT_ERROR, NODE_3_DOWN; no election (N3 was a follower) |
| Wheel test button, then double press | Both pairs fast and in step; cleared | One new term (633; the Pi had led 632) |

The fast/slow split follows the implemented rule: a node that hears no Pi
report flashes at 4 Hz, a node in error that still hears the Pi at 2 Hz. A
latched node stops listening, so it is the fast one; when the Pi is latched
nobody hears it and all flash at 4 Hz. The handout's wording for this case
was not re-read.

**Fault found: N3 reset by its watchdog twice**, 1 s after N2's clear and
1 s after the wheel's clear (`RESET cause=0x11 watchdog=1`), rejoining after
boot compaction. Reproduced without the user by latching and clearing the
leading Pi with SIGRTMIN/SIGRTMIN+1 (run 24); a latched follower Pi did not
trigger it (run 23). Program-counter sampling over SWD (DWT_PCSR, no halt)
showed no hang: N3 ran about 90% busy in steady state, and the resumed
leader's catch-up roughly doubled bus traffic (890 to 1,550 frames/s per bus)
for about 1 s, taking N3 to 100% and starving the priority-6 thread that
feeds the 1 s watchdog. Spinlock validation alone was about 12% of the CPU.

**Fix (firmware):** `CONFIG_SPIN_VALIDATE=n` (asserts stay on); the blink
thread sleeps until 250 µs before the next edge, waking on `blink_wake` or
every 5 ms, instead of polling every 200 µs; the clock copy is published on
receive only when a REF moved the clock. Flashed to both boards with history
backups; ELF SHA-256 N2 `1d6c64fb…`, N3 `cc3a5195…`. Same scenario after the
fix (run 25): both boards about 71% busy, 81% peak at the clear, **no reset**,
one clean NODE_1 set. Lamp-edge lateness windows stayed at 39–463 µs outside
mode changes (the counter also counts the phase flip of a rate change). That
latch took four terms (641–644): both Nucleos stood as candidates three times
before N3 won, about 0.5 s in all.

Not yet repeated by the user after the fix: the N2 and N3 button sequences,
and a scope skew reading with the new blink loop. Log at 18,739; N3 leads
term 644. Uncommitted. Logs: ignored `logs/lab5/20261116-checkoff/run21-step10/`
through `run25-load-fix-repro/`, `flash-load-fix/`.

## November 18 flap storm after N2's test clear (runs 26–27)

After the load fix, N3 leading term 644, Pi a follower. Direct skew over
about ten edges, user-read without signs: 0.45, 0, 0.25 (taken as −0.45 to 0,
mean −0.25 ms).

**N2 test button: failed.** The single press behaved as before. The double
press cleared N2's and N3's latches (console), but NODE_1 then cycled
DOWN/UP without stopping: the user saw irregular flashing and stopped. The
log grew from 18,751 to 21,397 (about 20 entries per second at the end)
until the Pi service was stopped by hand. No reset, no election (term 644).

Cause, from the capture: at about 15 entries per second the bus went from
1,220 to 2,165 frames per second per bus (each entry costs roughly 100
frames in APPENDs and replies on two buses). The Pi's kernel transmit queue
filled (`ENOBUFS`, about 30 per second; 39,000 frames per bus expired in its
outbox), its REPORTs fell from 50 to 14 per second, and the leader dropped
it; each DOWN/UP wrote six more entries, which kept the load up. The Pi's
control loop itself was on time. Whether running the cockpit at FIFO
priority reduces the kernel CAN worker's share in this state is not
established; steady-state transmit counters are clean under FIFO.

**Fix (Pi only):** when a committed NODE_1_DOWN arrives while the Pi is
announced, it goes quiet and re-qualifies, doubling the steady time for each
drop within 30 s of an announcement (2 s, 4 s … 30 s). New host test; 128
pass. On restart with the fix the Pi replayed the 2,650 entries quietly in
about 25 s and announced once (entries 21,398–21,401). **The N2 button
sequence has not been repeated with this fix.** Log at 21,401 of 30,000.
Uncommitted. Logs: ignored `logs/lab5/20261116-checkoff/run26-step10-repeat/`,
`run27-backoff/`.

## November 18 N2 clear lost on the way out (run 28)

With the back-off deployed and a log-growth guard running. N2 press: FAULT
test (sequence 11) on both buses, COCKPIT_ERROR and NODE_2_DOWN. Double
press 5.4 s later: the capture shows FAULT test again (sequence 12) and **no
FAULT clear on either bus**, while N2's console shows its own latch cleared.
N3 and the Pi stayed latched, so both pairs flashed at 2 Hz (user). No
storm: five entries in all, NODE_1 never dropped.

Cause: `send_both` gives a busy MCP2515 1 ms to free a transmit buffer and
then drops the frame (counted in `rejected_a/b`). The clear is sent once, in
the same instant that N2's heartbeats and Raft traffic resume. **Fix
(firmware):** a test press or clear waits up to 50 ms per bus
(`FAULT_SEND_WAIT_MS`). Flashed to both boards with history backups; ELF
SHA-256 N2 `8bf8b58c…`, N3 `a373c1af…`. The Pi's leftover latch was cleared
with SIGRTMIN+1. Not hardened: the Pi drops its own FAULT frames on
`ENOBUFS` in the same way (20 such errors in the storm). The user's
expectation, recorded: a clear must take effect without a visible delay.
**Not yet repeated by the user.** Pi leads term 645; log at 21,440.
Uncommitted. Logs: ignored `logs/lab5/20261116-checkoff/run28-n2-button/`,
`flash-fault-send/`.

## November 18 buttons after the FAULT send fix (run 29)

Pi leading term 645. **N2 and N3 press and double press: as expected (user).**
Wheel press and double press: the Pi's latch and both Nucleos' latches
cleared (FAULT clear sent and received), but the cockpit stayed in error
(user: "doesn't reset"), because NODE_1 stayed DOWN. Two causes:

1. The back-off added earlier counted the NODE_1_DOWN that follows the Pi's
   own test-button silence as a drop and doubled its wait each press: 1, 2,
   4, 8, 16, 30 s.
2. Independently, every announcement was followed about 0.3 s later by a
   real drop, with `ENOBUFS` on the Pi's ordinary CAN socket. Entries now
   arrive about 55 ms apart at an announcement (120 ms before the Nucleo load
   fix), so the Pi's APPEND replies fill its ten-frame transmit queue and its
   HELLO/REPORT frames expire. Not caused by FIFO priority (same at normal
   priority), nor by N2 leading (same under N3 after resetting N2).

**Fix (Pi only):** HELLO and the Pi's broadcast RPC frames (REPORT, votes) go
out on the priority socket already used for REF, ahead of the ordinary queue,
and their local echo is ignored; a NODE_1_DOWN within 1 s of the end of the
Pi's own silence no longer triggers the back-off. 129 host tests pass. After
the fix: one clean announcement (21,792–21,795), and two press/clear cycles
driven by SIGRTMIN/SIGRTMIN+1 with the Pi a follower each restored
COCKPIT_OK 0.32 s and 0.26 s after the clear with exactly six entries.
**Not yet repeated by the user with the wheel, nor with the Pi leading.**
N3 leads term 648; log at 21,807. Uncommitted. Open: N2 reports transmit
error-passive on both buses within seconds of boot; the Pi's MCP2515s report
about six receive overflows per second. Logs: ignored
`logs/lab5/20261116-checkoff/run29-buttons/`.

## November 18 wheel button after the presence-priority fix (run 30)

User: the wheel press and double press now work, including a second cycle
straight after the first. No reset on either Nucleo, guard not tripped. One
back-off hold of 1 s was logged when a NODE_1_DOWN arrived just over 1 s
after a clear. The Pi leads term 651; log at 21,858. **Step 10 is complete
by observation**: isolation of a follower and of the leader, and the test
button on N2, N3 and the wheel.

`lab5/pristine.py` now halts each Nucleo explicitly and freezes its watchdog
(the recipe used for every history backup this week) instead of expecting
the core to be halted after connecting under reset; its five tests pass. It
still has not been run on the bench.

## November 18 pristine cold start: steps 1 and 2

The user approved the wipe. `lab5/pristine.py --yes` at 07:17 (laptop time),
history at term 652 and 21,907 entries beforehand: all three stores backed
up and hash-checked (`logs/lab5/pristine/20261118-071724/`, second copy on
the Pi), sectors 6–7 erased and read back blank on both Nucleos, Pi store
cleared, Pi started and leading term 1, then both Nucleos released. **Result:
COLD START OK**, 44 s end to end.

- **Step 1:** N2 and N3 booted straight into term 1 with leader N1 (role
  follower, no candidate row); entries 1–11 are identical on both consoles
  (NOOP, NODE_1_UP, COCKPIT_OK, the Pi's two links, then each Nucleo and its
  links). The Pi reports role leader, synced, no error. The wheel proxy was
  running, so "error before the proxy, clear after valid input" and the
  LEADER/SYNC pins were not observed in this run.
- **Step 2:** 30 s `candump -L any` of the healthy default cluster,
  `lab5/tools/analyze.py candump`: REF from N1 in term 1 on both buses, mean
  interval 20.18 ms (5.8–35.6 ms as received), no missing cycle; empty APPEND
  to each follower every 100.24 ms mean; **0 vote and 0 pre-vote requests**;
  one FAULT frame per bus (not examined). Capture:
  ignored `logs/lab5/20261116-checkoff/step2-pristine/candump-healthy.log`.

Handout step 8, re-read: reboot everything with `LEADER=random`, an STM32
leads; power off that STM32 (new leader within 1 s, no failure mode); power
off the Pi (failure mode, held events, replay); "then the seed that makes
the Pi win, and step 6 again". In this implementation a seed fixes each
node's first election jitter only when all three start their Raft timers
together; a freshly booted node also refuses pre-votes for its first 60 ms.
With the Pi's boot taking about 20 s against 2 s for a Nucleo, the Nucleos
elect one of themselves before the Pi exists, whatever the seed.

## November 18 random-leader cold start and the Pi's SPI clock (run 32)

The user chose: show step 8's first three parts as written, and for "the
seed that makes the Pi win" bring the Pi up first and reset the Nucleos until
it wins, telling the TA that boot timing decides it.

`config.json` `default_leader` set to `random` for the bench (the repository
default stays `cockpit`; six cockpit host tests assume it). Both Nucleos
reflashed (ELF SHA-256 N2 `361789c4…`, N3 `d04579f5…`). `pristine.py` now
releases the Nucleos before starting the Pi when there is no pre-defined
leader (new test). Second wipe at 07:28, backups in
`logs/lab5/pristine/20261118-072757/`: **N2 won term 1** with N3, and the Pi
joined as a follower. On joining, NODE_1 was dropped three times in 1.5 s.

**Root cause of the Pi's transmit congestion all day:**
`/boot/firmware/config.txt` asked for `spimaxfrequency=1000000` on both
MCP2515 overlays (0.66 MHz measured in Lab 3), against 5.25 MHz actual on the
Nucleos. At about 1,200 frames per second per bus the Pi's SPI link was
saturated: 5.5 receive-overflow error frames per second on `can0`, `ENOBUFS`
bursts at every announcement. **Changed to 5000000** (MCP2515 limit 10 MHz;
5 MHz is the rate already in use on the Nucleos with the same modules); the
old file is `~/config.txt.before-spi5m` on the Pi. After a reboot: 0 overflow
error frames in 6 s, 0 `TX_ERROR`, backpressure 0–1.

With the log empty the Pi announced 11.8 s into boot and was dropped once
0.5 s later. **Fix:** no announcement before 25 s of uptime (`BOOT_SETTLE_S`;
systemd reports boot finished at 20.6 s). Next reboot: announced at 26.0 s,
exactly NODE_1_DOWN, COCKPIT_ERROR, then NODE_1_UP, both links and
COCKPIT_OK (entries 48–53). 131 host tests pass under the default config.
N2 leads term 1; log at 53. Uncommitted. The FL/RL skew and `pi_ref_send_us`
were calibrated with the slow SPI link and **must be re-measured**.

## November 18 step 8 in random-leader mode (run 33)

Random mode, cold-started with N2 leading term 1, Pi and N3 followers.

| Action | Lamps and LEDs (user) | Log |
|---|---|---|
| Power off N2, the leader | No hazards; ERR and DEG off on the remaining nodes | **The Pi won term 2**; N3 saw the new term within one 0.2 s console interval of N2's port vanishing; NODE_2_DOWN, no COCKPIT_ERROR |
| Power N2 on | Front pair flashed briefly | NODE_2_UP and its two links, three entries |
| (N2 off again for 277 s, then on) | | NODE_2_DOWN; later NODE_2_UP and links |
| Power off the Pi, then leading term 2 | Fast hazards, as expected | Both Nucleos `HEALTH reasons=0x8` at report age 66 ms; N2 candidate and leader of term 3 in the same console interval; NODE_1_DOWN, COCKPIT_ERROR |
| Power the Pi on | One clean switch, as expected | Pi a follower of N2; entries 65–67 marked replayed on the Pi, then NODE_1_UP, both links and COCKPIT_OK live |

ERR and DEG off with N2 unpowered is the designed behavior: an STM32
failure alone is not the failure mode (handout step 8), and DEG marks a bus
on which a node hears nobody, which is not the case while the Pi and N3 are
on both buses.

**Step 8 is complete** with one stated difference from the handout: the Pi
led in random mode because it won the election after the STM32 leader was
powered off, not because of a boot-time seed. Then `default_leader` was
restored to `cockpit`: both Nucleos reflashed (ELFs identical to the
`flash-fault-send` builds, `8bf8b58c…` and `a373c1af…`), config redeployed,
131 host tests pass. N3 leads term 6; log at 99. Uncommitted.

## November 18 relayed skew after the SPI change (run 34)

N3 leading term 6, relayed through the Pi (N2 off B, N3 off A), about ten
edges, user-read: **min −1.09 ms, max +0.01 ms, mean −0.80 ms. Fails at the
minimum.** With N3 leading, negative means the follower N2 is ahead, so the
relay path was over-credited by about 0.8 ms.

From the capture (9,867 relayed REFs): Pi kernel receive to transmit-complete
now averages 2.55 ms (3.01 ms at the old SPI clock); the stamp credited
3.03 ms, 0.47 ms too much, which is the `pi_ref_send_us` allowance measured
against the slow link. The remaining 0.33 ms is attributed to the Pi's
kernel now stamping a received frame sooner after the wire, so the shared
780 µs hop is too long for frames the Pi receives; that part is inferred
from the scope total, not measured separately.

**Recalibration (Pi only):** `pi_ref_send_us` 500 → 0, and a new
`pi_can_delay_us` = 450 used by the Pi in place of `can_delay_us`. Predicted
relayed range about −0.3 to +0.8 ms. Deployed; 131 host tests pass.
**Not yet measured.** Uncommitted. Logs: ignored
`logs/lab5/20261116-checkoff/run34-skew-spi5m/`.

## November 18 relayed skew after recalibration (run 35)

N3 leading term 6, relayed through the Pi, about ten edges, user-read:
**min −0.27 ms, max +0.33 ms, mean +0.05 ms.** With `can_delay_us` 780,
`pi_can_delay_us` 450, `pi_ref_send_us` 0 and the Pi's SPI clock at 5 MHz,
the STM32-led relayed case (step 9) is centred and inside the limit. The
direct STM32-led reading (−0.45 to 0 ms, signs assumed) predates the SPI
change, which does not touch that path.

## November 18 PPS across a Pi-to-STM32 handover (run 35, first attempt)

Scope: CH1 = N3 PPS, CH2 = N2 PPS (PA8, D7, CN10-23), delay CH1 rising to
CH2 rising over about ten pulses, user-read.

| | Min | Max | Mean |
|---|---|---|---|
| Pi leading term 8 | −1.64 ms | +0.99 ms | −0.005 ms |
| After unplugging the Pi (N3 leading term 10) | −0.55 ms | −0.18 ms | −0.30 ms |

The handover took two terms (9 and 10) in about 0.2 s. Two defects:

1. **PPS jitter.** The pulse was written by the protocol thread, which runs
   below CAN receive and takes `raft_lock`, as the blink thread did before
   its fix. **Fix:** the edge thread (priority 0) now drives PPS: high on the
   whole global second, low 1 ms later.
2. **A 0.3 ms shift between the two boards at handover.** Under the Pi both
   boards carry the same error and their difference averages zero; under an
   STM32 leader the follower sat 0.3 ms ahead, so each board's phase moves
   by that much over the few REFs after a handover, more than the 100 µs
   limit even though no single correction exceeds 50 µs. The direct delay
   was last centred before `CONFIG_SPIN_VALIDATE=n` made the Nucleos handle
   a received REF sooner. **Recalibration:** `can_delay_us` 780 → 480, and
   `pi_ref_send_us` 0 → 300 so the path through the Pi keeps its total.

Both Nucleos reflashed with history backups (ELF SHA-256 N2 `73967960…`,
N3 `922df695…`), config redeployed to the Pi, 131 host tests pass. **Not yet
measured.** This moves every skew case: direct and relayed STM32-led, and
the Pi-led relay through N2, all need one reading again. Uncommitted.

## November 18 PPS across the handover, after the fixes (run 36)

Same scope setup, about ten pulses each, user-read.

| | Min | Max | Mean |
|---|---|---|---|
| Pi leading term 12 | −0.27 ms | +0.36 ms | −0.006 ms |
| After unplugging the Pi (N2 leading term 13, one election) | −0.19 ms | +0.20 ms | −0.005 ms |

**The mean difference between the two boards' PPS moved by 1 µs across the
handover** (limit 100 µs), and the pulse-to-pulse spread fell from 2.6 ms to
0.6 ms and 0.4 ms. Both boards logged `HEALTH reasons=0x8` at a Pi report
age of 66 ms. This is the step 6 phase evidence; brake latency on the scope
is still not taken.

## November 18 final STM32-led skew, and N3's bus-B transmitter (run 37)

N2 leading term 13, `can_delay_us` 480, `pi_can_delay_us` 450,
`pi_ref_send_us` 300, PPS in the edge thread.

- **Direct:** user-read 0.26, 0.17, −0.06 (taken as min −0.26, max +0.17,
  mean −0.06 ms). Passes.
- **Relayed through the Pi: no valid reading.** The scope minimum grew past
  −200 ms because N3 was not synchronized at all. Committed entries:
  CANLINK_2_B_DOWN, then at the N3-A pull CANLINK_1_B_DOWN and NODE_3_DOWN.

Cause: **N3's bus-B transmitter had stopped completing frames** long before
the pulls. Its console shows `completed_b` frozen at 65,933 while
`rejected_b` climbed about 360 per second, bus B still error-active and
receiving, no INT kick. From run 36 the freeze began within 5 s of the Pi's
power being plugged back in (N3's bus-B completions were normal while the Pi
was off). With bus A connected nothing shows it, because every N3 frame also
goes out on A; with N3 on bus B only, it is mute. This matches the October
21 note "N3 CAN B latched dead until reset". A checkoff that power-cycles
the Pi (steps 6–7) and then runs step 9 would hit it.

**Fix (firmware):** the 20 ms monitor restarts a controller (`can_stop`,
`can_start`) that has finished no transmission for 25 periods while sends to
it are refused, at most every 2 s; `TX_COUNTS` now reports `restarted_a/b`.
An unplugged bus is restarted too, which only aborts frames nobody would
acknowledge. Flashed to both boards with history backups (ELF SHA-256 N2
`1bc495a2…`, N3 `873a53de…`). With the jumpers still out after the flash,
N2 shows `restarted_b` and N3 `restarted_a` counting as expected, N3's bus B
completing normally, and all three nodes alive through the relay.
**Not yet shown:** that the restart clears the latched state itself; that
needs a Pi power cycle. Uncommitted.

The user reports the cloud mirror was unreachable all day. The uplink runs
in its own thread with a 1,000-row bounded queue and 1 s/2 s HTTP timeouts,
and the control loop only appends to that queue under a short lock, so an
unreachable server does not delay it; `cloud-ack.txt` does not exist on the
Pi, consistent with no upload ever succeeding. Nothing today was measured
with the uplink actually uploading.

## November 18 relayed skew with final values, and the recovery in action (run 38)

N2 leading term 15, relayed through the Pi, about ten edges, user-read.

| Reading | Min | Max | Mean |
|---|---|---|---|
| Fresh firmware, jumpers still out | −0.60 ms | +0.22 ms | −0.03 ms |
| After a Pi power cycle and fresh pulls | −0.13 ms | +0.37 ms | +0.10 ms |

**Both pass.** The Pi power cycle wrote one clean NODE_1 set each way.

The controller restart fired for real: this time N3's bus-B transmitter
did not stall at the Pi's power-on but within about 2 s of N3's bus-A jumper
being pulled (`completed_b` advanced 1,539 in 5 s instead of about 2,000,
`rejected_b` +359). `restarted_b` went 0 → 1 and completions resumed; in run
37 the same state was permanent. Cost: NODE_3 dropped and returned twice
over 3 s, ten extra entries. So the trigger is not specific to the Pi's
power; both occurrences followed an electrical event on the bench.

## November 18 Pi-led skew with final values, and a clean step 5 (run 39)

Pi leading term 19, about ten edges, user-read.

| Step | Min | Max | Mean |
|---|---|---|---|
| 3, direct | −0.20 ms | +0.35 ms | +0.014 ms |
| 5, N1 off B and N3 off A (RL relayed through N2) | −0.18 ms | +0.05 ms | −0.07 ms |

**Step 5 now has the clean transition on record:** exactly two link entries
for the two pulls (323 CANLINK_1_B_DOWN, 324 CANLINK_3_A_DOWN), `EVENT_N2`
at index 325 on both N2 and N3, term 19 throughout. The N3-A reinsertion
wrote one UP and then a NODE_3 down/up with link entries (contact bounce).

### Skew summary with the final configuration

`can_delay_us` 480, `pi_can_delay_us` 450, `pi_ref_send_us` 300, Pi SPI
clock 5 MHz, lamp edges and PPS from the priority-0 edge thread.

| Case | Min | Max | Mean |
|---|---|---|---|
| Pi-led, direct (step 3) | −0.20 ms | +0.35 ms | +0.01 ms |
| Pi-led, relayed through N2 (step 5) | −0.18 ms | +0.05 ms | −0.07 ms |
| STM32-led, direct (step 9) | −0.26 ms | +0.17 ms | −0.06 ms (signs assumed) |
| STM32-led, relayed through the Pi (step 9) | −0.60 ms | +0.22 ms | −0.03 ms |
| STM32-led, relayed, after a Pi power cycle | −0.13 ms | +0.37 ms | +0.10 ms |
| PPS, N3 to N2, Pi leading | −0.27 ms | +0.36 ms | −0.006 ms |
| PPS, N3 to N2, after handover to an STM32 | −0.19 ms | +0.20 ms | −0.005 ms |

All inside 1 ms; the handover moved the PPS mean by 1 µs.

### Not observed or still open on November 18

- Step 1: hazards before the wheel proxy and their clearing after input; the
  LEADER and SYNC pins.
- Step 6: brake latency on the scope (boards log the error at 66 ms).
- Step 8: the Pi led in random mode by winning an election, not through a
  boot-time seed.
- N3's CAN controllers stall on bench electrical events; auto-restart
  recovers them at a cost of about ten entries.
- Reinserting a jumper can write several link entries (contact bounce).
- Some failovers take two to four terms (split votes) within about 0.5 s.
- Nothing was measured with the cloud uplink actually uploading.

## November 18 cloud mirror test, first part

The mirror is reachable and its containers are up, but it was stale for 78
minutes because of the pristine start, not an outage. It still holds the old
history through index 21,907 (term 652), so it answers **409 Conflict** to
entry 1 of the new history, as `lab5/cloud/README.md` says it will until its
Redis data is cleared. A defect made that invisible: `Uplink.once()` posted
the entry first and raised on the refusal, so no heartbeat was ever sent.

**Fix (`pi/uplink.py`):** the heartbeat is sent even when the entry is
refused and carries `uplink_error`; the dashboard line shows "Upload
refused". New host test; 132 pass. Deployed to the Pi. The mirror now
reports a live heartbeat (leader N2, term 20, length 340), `pending` 340,
`last_ack` 0-0, `uplink_error` 409. With the uplink retrying once a second
the Pi logged no loop of 40 ms or more and was not dropped.

**Not done:** clearing the mirror's Redis (needs the user's go-ahead: it
deletes the old history copy on a team member's VM), after which entries can
flow and the upload, resume-after-outage and load-while-uploading checks can
run. The dashboard change is not yet on the VM. Uncommitted.

## November 18 cloud mirror test, second part

With the user's approval: the dashboard file was copied to the VM and the
app container rebuilt, then the mirror's Redis was cleared (`FLUSHDB`).

| Check | Result |
|---|---|
| Backlog upload | 340 entries accepted and acknowledged in about 12 s; `cloud-ack.txt` 340-0; `missing_entries` 0 |
| Content | The mirror's stream (index, term, event) is identical to the Pi's `display.sqlite` for all 340 entries |
| Live entry | A SIGUSR1 diagnostic event (341) was on the mirror at the first poll 1 s later |
| Mirror outage | App container stopped about 30 s (nginx 502): three events committed on the car, ACK held at 341; on restart all three were on the mirror within 3 s, no gap |
| Pi absent | Pi service stopped 9 s: `stale` true; restarted: `stale` false, entries 345–346 flagged replayed and 347–350 live, ACK 350-0 |
| Access | `/api/state` and `/ingest/heartbeat` without credentials return 401 |
| Effect on the car | Through all of this the Pi logged no loop of 40 ms or more (worst 24 ms) and was never dropped |

Not done: a scope skew reading with the uplink on against off, and a
physical Pi power cycle watched on the dashboard. N2 leads term 20; log at
350. Uncommitted.

Remaining report evidence: measured drift ratio/correction and PPS jitter, FL/RL skew, handover phase, failover/brake latency, equal committed logs/network snapshots for the three body scenarios, and any unpassed limits. The three technical discussion sections have one-page limits. All team members need to explain quorum, votes/terms, commit versus append, pre-vote, phase versus rate correction, and discovery versus committed routing.
