# Lab 3 Parts 4–5 demo: three zones, dual CAN, N2 relay

The checkoff application for the Lab 3 handout's Part 5, including the Part 4
relay. `lab3_wcet_baseline/` remains the measured Part 3 firmware; this app
reuses its timing instrumentation, PID workload and steering mapping by path
instead of copying them. Pins: [LAB3_PINOUT.md](../doc/LAB3_PINOUT.md#lab-3-part-5-demo-allocation).

**Status:** the sources follow the hard numbers of Lab 1, the Lab 3 handout and the
[October 22 student clarification](../doc/18-449_649%20Lab%203%20-%20Student%20clarification%202026-10-22.pdf)
(see [Spec alignment](#spec-alignment-october-23)). That build is flashed and the
matching cockpit deployed. At 06:15, after the Pi's bus-A transmit fault cleared,
all three zones were OK on both buses with flat error counters. The user traced
the fault to loose wiring and fixed it (see the known behaviors). Fault-injection and timing checkoff steps have not been run.

| Path | Role |
|---|---|
| `stm32_zephyr/` | N2 (front) and N3 (rear) Zephyr app; one build per zone |
| `pi/cockpit.py` | N1 cockpit: UDP → CTRL/BLINK/HB_N1, HB_MON, FORCE_RX, LEDs |
| `tests/test_host.py` | Builds the C zone-state, frame-history and protocol code with host gcc |
| `pi/test_*.py` | Cockpit behavior on python-can virtual buses, plus protocol/state units |

## Design decisions

**Relay (Part 4.2).** Only N2 relays, because only N2 is meant to stay on both
buses. It forwards a CRC-valid first copy whose origin is N1 or N3 to its other
bus only while **that origin has sent no heartbeat on the destination bus for
60 ms** (`zone_monitor_present`, the R4.7 degraded threshold), and unless that bus
has already delivered the copy. Healthy buses therefore carry no relayed
copies. In scenario (c) relaying starts within 60 ms of the pull (the first CTRL
after it can be up to about 80 ms late); no zone errors on a stale CTRL, so the
system stays up through that gap. The frame history (`frame_history.c`) is
ported from Tianyi's `lab3-relay-immediate` branch.

Why the gate (October 23): the earlier immediate relay also forwarded frames
whose origin was present on the destination bus. With N3 off bus B, bus B held
only the Pi and N2; N2's unchanged copy of a Pi frame sometimes started at the
same bit as the Pi's own copy. Two bit-identical transmitters with no third node
get no ACK, so both retried in lockstep forever: Pi can1 and N2 bus B went
error-passive and silent 19 s and about 2 min after restarts, with no kernel
message, and stayed so until can1 was re-initialised. With the gate flashed
(`logs/lab3-can/20261023-083008-demo-build-relay-gate/`), N3 off bus B ran
4 min with zero dead intervals while N2 relayed N3's frames onto B.

- **Loop freedom:** N1 and N3 never forward. N2 claims at most one forwarding
  attempt per (ID, source, seq) per destination bus. A controller never receives
  its own transmission. Every node drops frames it originated when N2 echoes them
  back.
- **Dedup:** one dispatch path per node records the heartbeat per bus first, then
  drops any copy of an (ID, source, seq) seen within **20 ms** on *either* bus. A
  relayed copy can arrive on the same bus as the direct one, so a same-bus repeat
  inside the window is a duplicate. After the window, the same sequence is a new
  message (4-bit wrap = 320 ms at 20 ms). The window exceeds the measured 2.6 ms
  Pi can0→can1 write gap. Every payload is idempotent, so a late copy is harmless.
  FAULT's source is its reporter byte, because several zones send FAULT.
- **Priority:** RELAY is priority 2 on N2, below RX dispatch (1) and above
  STEER (3). The MCP2515 driver threads are cooperative and run above all of them.
  RELAY uses its own queue; dispatch enqueues before processing the frame locally.

**Error state (R3/R4.5).** One pure module, `zone_state.c`, mirrored by
`pi/zone_state.py`, holds every threshold. Every value below is a lab number:

| Rule | Value | Source |
|---|---|---|
| Peer zone failed: no heartbeat on either bus | 66 ms | R4.5 three missed heartbeats at 20 ms +10 %; clarification chain "3 missed heartbeats (66 ms)" |
| Bus degraded: no frame from any other node while the other bus has traffic | 60 ms | R4.7 |
| Isolated: no heartbeat from any zone on either bus | 60 ms | R4.7; own fail-safe within 100 ms |
| N1 failed: no UDP update, stops HB_N1 until the stream resumes | 100 ms | Lab 1 cockpit zone |
| CTRL refresh without an update | 40 ms | R4.4 "no less than every 50 ms", 10 ms Linux margin |
| One press | < 50 ms apart | R2.5 debounce |
| Double press | 500 ms | R3, clarification |
| FAULT / BLINK spacing per sender | 20 ms | Catalog minimum interval |

A zone is in error when it is latched, a peer zone has failed, or it is isolated;
an STM32 zone also stays in error until its first valid CTRL, and N1 while its UDP
stream is down. Stale CTRL is not an error (R3 lists no such trigger): N1 sends
CTRL at least every 50 ms while it is alive, and its failure stops HB_N1. A
test-button press, an out-of-range CTRL, a bad-CRC CTRL or (on N1) a malformed
wheel datagram latches and sends FAULT. Every receiver latches on that FAULT. A
test-button press also stops that node's heartbeats, as the clarification
requires, so peers enter error even if the FAULT is lost. A second press 50–500 ms
later on any zone's button sends FAULT clear, which releases every latch and
resumes any silenced heartbeats. The press FAULT and the clear wait for the 20 ms
FAULT slot; repeatable reports (bad input, zone loss) inside it are dropped. FAULT
`ZONE_LOST` (reason 4) is informational: each node detects heartbeat loss itself
and recovers without a clear, so restoring an isolated node returns to normal
without a reset.

**Degraded LEDs (R4.7).** DEG_A on a node means it has received no frame from any
other node on A for 60 ms while B still has traffic. Pulling one node's A jumper
lights only that node's DEG_A, because the others still hear each other on A. An
isolated node lights neither LED: neither bus has traffic. Checkoff step 5 wants
the LED within 60 ms of the pull, so the LED switches when the 60 ms elapse, not
on the next 20 ms HB_MON: STM32 dispatch waits on its queue with that deadline as
the timeout, and the cockpit's main loop wakes for it.

**Outputs.**
- N2 SRV is a 50 Hz servo pulse from the Lab 2 calibrated mapping (1200/1600/2000 µs). It keeps tracking CTRL in the system error state (R3). When N2 itself has failed (its own test press or isolation) it holds the last pulse (R4.7 "steering held"). No pulse is output before the first valid CTRL.
- N3 PWM_OUT is 10 kHz with duty equal to throttle %, and DIR_A high selects forward.
- Brake or error on N3 drops DIR_A and holds PWM_OUT high: the L298 enable-high/equal-input brake. PWM_SET toggles after each timer write, as in Lab 2.
- Blinkers switch on BLINK reception so both zones change on the same frame. In error an STM32 starts hazards at once on a local 500 ms timer, so an isolated zone flashes within 100 ms (R4.7). Every hazard BLINK from N1 re-phases that timer, keeping the zones in unison and the flashing going if BLINKs stop.
- The Pi is the blinker master and uses the Lab 2 paddle map (bit 5 left, bit 4 right, steering auto-cancel). It sends BLINK on a change and every 500 ms toggle, never within 20 ms of the previous BLINK. Every mode, hazards included, runs at 1 Hz. The team chose the Lab 3 BLINK row over Lab 1 S4's 2 Hz hazard where the two documents conflict.
- FORCE carries the Lab 3 dummy counter. N1 does not send UDP force to the proxy: the team follows Lab 3 ("S3 force feedback: No. Dummy payload only.") over Lab 1 R2.3's 50 ms UDP force message.

**Other Part 5 items.**
- Two MCP2515 devices come from devicetree, with `can_add_rx_filter` for the 7 catalog IDs on each.
- `send_both()` bumps the per-ID sequence once and queues A then B. The first pass uses `K_NO_WAIT`, so a disconnected bus's full mailbox cannot delay the other copy.
- IWDG is set to 1 s and fed only by HB_MON.
- The ISR only gives a semaphore. The CAN callback only enqueues. Shared state is mutex-protected.
- The MCP2515 recovers from bus-off in hardware; per-bus state changes are counted on the console.
- HB_MON re-pends a CAN INT EXTI line that stays low across two checks. This targets the "CAN B latched dead" incidents in `doc/LAB3_CAN_BRINGUP.md`; the fix is untested.

## Physical bus labels

AGENTS.md records crossed module labels. Pi `can0` connects N2 module B and N3
module A; `can1` connects N2 module A and N3 module B. This app calls Pi **can0
bus A**. Build the board whose module A (CS PB6 / INT PA10) sits on can1 with
`swap_ab.conf`; that is ST-LINK 124020 per the October 21 records. Swapping follows
the board, not the zone. Confirm with the per-bus console counters before the
fault tests, and label breadboard rows A_H/A_L on the can0 bus.

## Build and flash (this Windows host)

```powershell
$ws = "$env:USERPROFILE\zephyrproject"; $app = "C:\Users\13982\18649_team4\lab3_demo\stm32_zephyr"
$env:Path = "$ws\.venv\Scripts;" + [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
Set-Location "$ws\zephyr"
west build -b nucleo_f401re -d "$ws\build-lab3-demo-n2" $app -- "-DEXTRA_CONF_FILE=$app\prj_n2.conf;$app\swap_ab.conf"
west build -b nucleo_f401re -d "$ws\build-lab3-demo-n3" $app -- "-DEXTRA_CONF_FILE=$app\prj_n3.conf"
pyocd flash -u <st-link serial> -t stm32f401retx "$ws\build-lab3-demo-n2\zephyr\zephyr.hex"
```

Drop `swap_ab.conf` from N2 and add it to N3 if the roles move to the other
boards. The serial console (115200, ST-LINK VCP) prints state, CAN state and
INT-kick counts, TX counts, relay counts and `OBS_TASK` maxima every 5 s. Capture
it to `logs/lab3-can/<timestamp>-<COM>.log`: that stream is also the crash report
(`CONFIG_FAULT_DUMP=2` plus a logged coredump; keep the matching `zephyr.elf`).
`timing probe NAME` selects a task pulse on PC8, as in the baseline; `relay` is
available on N2.

## Test panel (no command line)

Double-click **`lab3_demo/test_panel.pyw`**. It opens the course wheel window,
running under the course checkout's `.venv` with 20 ms timers and the Pi address
from the `wheelpi` alias, plus a **Lab 3 tests** dialog. The equivalent command
is `windows/start_wheel_proxy.py --lab3`. The dialog covers:

| Control | Does | Checkoff step |
|---|---|---|
| Start (Restart while running) / Stop, *Bench input* | `start.py [--restart]` / `stop.py`; uses the [local password file](#run-the-cockpit-pi), or asks for the Pi sudo password on each start and passes it on stdin only. Restart redeploys the current `pi/` code and keeps the session's bench setting. *Bench input* adds the laptop sender for use without the wheel | session |
| ERR, DEG_A, DEG_B, N2, N3, LATCH lamps | N1's live state from the cockpit's per-second `STATUS` line | 1, 5–8 |
| Pause bench input | Sender stops, as if the proxy stopped; every zone enters error | 1 |
| Bus traffic (3 s candump) | Per-ID rate on can0/can1 and recent sequence nibbles | 2 |
| N1 test press / Clear all faults | Same as one wheel A press, or a double press | 9 |
| Bad CTRL: throttle 101 / CRC | Next CTRL out of range, or with a bad CRC | 10 |

The event pane streams state, degraded, FAULT, injection and TX-error events
from the Pi. Signals go to the recorded cockpit PID only after checking its
command line. GUI logs and crash reports go to `logs/wheel-gui/`. Don't run the
bench sender while the wheel window is connected and transmitting: the cockpit
would then get two UDP streams.

## Run the cockpit (Pi)

From the laptop. Sudo uses the password in `lab3_demo/pi_sudo_password.txt`,
one line, gitignored because the repository is public. Without that file,
`start.py` asks once in the terminal:

```powershell
python lab3_demo\start.py              # course proxy supplies UDP; add --synthetic for a bench sender
python lab3_demo\stop.py
```

`start.py` checks the can0=spi0.1 / can1=spi0.0 mapping and that GPIO
5/6/12/17/22/23/27 are free. It brings both links up at 500 kbit/s with
`restart-ms 50` (R4.8: bus-off recovery within 100 ms of restoration), taking down
a link that is up with another restart time, copies `pi/` to a fresh
`~/.local/state/team4-lab3/demo-<id>/` folder and runs its tests there. It then
starts `cockpit.py` detached and applies `chrt -a -f 1`, FIFO 1 as measured in
Part 3, re-verified on every start. Ownership is recorded in
`logs/lab3-can/demo/state.json` (ignored). The measurement bridge in
`logs/lab3-can/pi-scope/` uses the same CAN links and GPIO lines, so run only one
of the two sessions. Bad-input injection on the Pi:

```sh
kill -USR1 <pid>   # next CTRL has throttle 101: N2/N3 enter error and send FAULT
kill -USR2 <pid>   # next CTRL has a corrupted CRC
kill -s RTMIN <pid>     # N1 test press (latch); RTMIN+1 clears every zone
```

The wheel A button is N1's test button; a single press latches and stops HB_N1,
and a second press within 500 ms clears. Logs go to the session folder (standalone runs default to
`~/.local/state/team4-lab3/demo/<start time>/`): `events.csv`
holds state, degraded, FAULT, TX-error and per-CTRL `UDP_TO_CMD_TX` latency, and
`crash.log` holds tracebacks and faulthandler dumps. `--no-gpio` runs without
libgpiod.

## Host tests

```sh
python lab3_demo/tests/test_host.py                       # gcc: zone state, history, C/Python protocol
cd lab3_demo/pi && python -m unittest discover -p "test_*.py"   # needs python-can
```

## Deployment, October 21

Images are from `logs/lab3-can/20261021-093035-demo-build/` (binaries, ELFs,
configs, sources, SHA-256). N2 `n2swap_ab` was flashed to ST-LINK 124020 (COM6)
and N3 `n3` to 171333 (COM4), both with pyOCD under-reset. The Pi cockpit was
started by `start.py --synthetic` and runs under FIFO 1 on all threads; its state
file is `logs/lab3-can/demo/state.json`.

Verified with all buses connected and the synthetic sender at 20 ms:
- **Startup:** both MCUs booted into ERROR, heard each other on both buses, and
  left ERROR when N1 started. All three zones report OK with both peers alive.
- **LEDs and transmit:** no degraded bus on any node. CAN state was error-active
  on all four MCU controllers with zero transmit rejects or failures.
- **Traffic:** a 3 s candump showed IDs 010/100/101/102/200/300 on both can0 and
  can1. FAULT stayed silent as expected. HB ran at 50/s per bus and FORCE at 20/s.
- **Healthy-bus relay overhead:** CTRL showed 155 frames on can0 and 181 on can1.
  N2 often receives the can0 copy before the Pi's can1 write lands, so it relays
  about 13 frames/s onto the other bus, mostly onto B.
- **Receive counters:** no INT re-kicks, no receive drops and no bad CRCs.

Console maxima are elapsed times, not scope results: STEER 186 µs (includes the
PWM write), DRIVE 187 µs, RELAY 413 µs, can_tx 350 µs. Evidence:
`logs/lab3-can/20261021-093718-demo-flash-n{2,3}-*.log`, `20261021-093849-demo-live-COM{4,6}.log`
and `20261021-093849-demo-pi-check.log`.

## Clarification alignment, October 23

Changes for the October 22 student clarification, host-tested (31 Pi tests on the
Pi's python-can, 3 host C tests) and built. The images and matching sources are
in `logs/lab3-can/20261023-041626-demo-build-clarification/` (`n2swap_ab`, `n3`).
On October 23 they were flashed under reset with pyOCD: N2 to ST-LINK 124020 (COM6),
N3 to 171333 (COM4). The cockpit was redeployed with `start.py --synthetic`.
Healthy-bus startup was re-verified: all three zones OK, no degraded bus, all
four controllers error-active, zero TX rejects/failures, receive drops, bad CRCs
or INT re-kicks; N2 relayed 527 frames with no failures. The cockpit counted 4
`bad_frame` receptions, not yet explained. Evidence:
`logs/lab3-can/20261023-041954-demo-flash-n{2,3}-*.log` and
`20261023-042341-demo-live-COM{4,6}.log`. The test-press heartbeat silence and
500 ms double press have not been exercised on hardware.

- **Test button:** the pressed node sends one FAULT and stops its heartbeats until
  any FAULT clear. The double-press window is 500 ms (was 400 ms). The STM32
  console state line adds `hb_silenced`.
- **RELAY_TX (#6):** toggles after the bus-B `can_send` returns, not before it.
- **CMD_TX (#1):** the Pi toggles it right after the first CTRL write (bus A)
  returns, and `UDP_TO_CMD_TX` uses the same boundary. The `lab3_wcet_baseline`
  bridge still marks after both writes, so its Part 3 results use a different
  boundary.
- **Already matching:** CAN_RX_A toggles when dispatch first gets a frame (#2, #5).
  DIR_A drops on a brake frame (#3). The STM32s send with a TX callback.
- **Blocking term B:** `send_both()` holds no lock across the two buses. The
  MCP2515 driver releases its per-device mutex before its SPI writes, and each
  SPI transaction locks the shared bus only while it runs. B is one frame load
  (#4), not 2 × #4.

## Spec alignment, October 23

The sources were audited against every hard number in Lab 1 R1–R4, the Lab 3
handout and the clarification, and changed where they differed: the threshold
table under [Design decisions](#design-decisions); one CTRL per UDP datagram
instead of one per drained batch, plus a refresh after 40 ms; N1 failure (HB_N1
stops) after 100 ms without UDP; no stale-CTRL error; R4.7 degraded/isolated
definitions with the LED switching at exactly 60 ms; N2 steering kept in the
system error state; immediate local hazards in error; the 50 ms single-press rule
from the previous raw press; 20 ms FAULT/BLINK spacing; a malformed wheel datagram
as bad input; `restart-ms 50`. Where Lab 1 and Lab 3 conflict, the team chose Lab 3:
hazards at 1 Hz (BLINK row, not S4's 2 Hz) and no UDP force message ("S3: No"). The
MCP2515 leaves bus-off by itself after 128 × 11 recessive bits, so the STM32 side
needs no recovery code for R4.8; the Pi uses the kernel's `restart-ms`.

Tests: 43 Pi tests on the Pi's python-can and 3 host C tests pass; both images
build. Flashed under reset on October 23 at 05:15: N2 `n2swap_ab` to 124020 (COM6), N3
to 171333 (COM4), from `logs/lab3-can/20261023-051503-demo-build-spec/` (the 05:06
archive was flashed first and superseded by the press-chatter fix). The cockpit
was redeployed with `start.py --restart --synthetic`. Live checks were blocked by
the hardware faults under [Known behaviors](#not-yet-verified); healthy-bus startup
has not been re-verified on this build.

## Not yet verified

All of the following needs hardware: every checkoff step, both relay directions,
bus-off/reconnect recovery times, the INT re-kick, front/rear blink skew, the
relayed brake chain, and PWM waveforms on PB4.

Known behaviors to watch on hardware:
- Taking a Pi CAN link down (`ip link set canX down`) kills the cockpit's python-can receive thread for that bus (`CanOperationError: Network is down` in `crash.log`); run `start.py --restart` afterwards. The October 23 bus-B lockups that prompted link restarts were the immediate-relay lockstep described under [Design decisions](#design-decisions), not a Pi or wiring fault.
- Wi-Fi delays wheel UDP. On October 23 the laptop (CMU-SECURE) and Pi (CMU-DEVICE) shared one AP on channel 149. A passive Pi capture got all 3001 synthetic packets with none lost, yet 27 arrival gaps exceeded 60 ms (up to 146 ms), each followed by a burst of 4–7 held packets. The laptop's 20 ms loop never woke more than 20.7 ms apart. Under the old 60 ms CTRL rule this flashed whole-system hazards 70 times in 272 s. Under the Lab 1 rule now implemented, only gaps of 100 ms or more fail N1. With Pi `wlan0` power save off (not persistent across reboot), that happened 7 times in about 246 s, every one `udp_ok=False`; that error is the required behavior. Removing it needs a link without these gaps, such as wired Ethernet between the laptop and the Pi.
- Bus-A and Pi SPI hardware faults, October 23 (evidence in `logs/lab3-can/20261023-051300-pi-can-stall/`). At Pi uptime 1922 s, with no software change, both Pi controllers stopped transmitting (ENOBUFS, kernel `hard_xmit called while tx busy`). Bringing the links back up failed several times with `MCP251x didn't enter in config mode`, the symptom of the earlier SPI wiring fault, and the Pi then received 4419 CRC-bad frames in 26 s. After the 05:15 reflash, N3 printed nothing: its CPU was servicing EXTI10 (PA10, CAN A INT) continuously, while N2's bus-A controller was error-passive and every Pi bus-A transmit failed. Check the Pi's MCP2515 SPI/3V3/GND jumpers and the bus-A rail and jumpers before further hardware tests.
- Recheck at 05:30 (`logs/lab3-can/20261023-053047-demo-live-COM{4,6}.log`): N3 had recovered. Over 30 s both STM32s were OK with all zones alive, no degraded bus, both controllers error-active and no new rejects, INT re-kicks, state changes or relay failures. The Pi's can0 still received, but its TX packet counter stayed at 193430 while its error-warning/passive counters rose. The cockpit logged 87275 bus-A TX errors from its start at 3438.9 s onward, with no bus-A errors seen by N2 or N3. N2 relayed about 107 frames/s, N1's traffic copied from B onto A. The Pi can0 link was left running at the user's request; a link down/up or the Pi module's bus-A connection is the next thing to check. In the same window, 47 UDP gaps exceeded 100 ms (maximum 149.7 ms), each briefly failing N1 as Lab 1 requires.
- Recheck at 06:15 (`logs/lab3-can/20261023-061526-demo-live-COM{4,6}.log`), with the cockpit still running: the Pi's bus-A TX errors (about 6150/min) stopped at 6956.5 s and can0 TX packets rose about 117/s. A 3 s candump on can0 showed 010/100/101/102 at 50/s, 200 at 2/s and 300 at 20/s. N2 relayed 7 frames in 5 s, down from about 107/s, so N1 again reaches A directly. N2 and N3 were OK, all zones alive, no degraded bus, both controllers error-active and every error counter unchanged since 05:30. The user reports the cause was loose wiring, which they fixed (which wire was not recorded).
- Frames queued on a disconnected bus, up to 3 in the MCP2515 or the Pi's txqueue, are sent when the jumper returns. A stale CTRL can be applied for one 20 ms period.
- The latch is carried only by FAULT frames, so a node that reboots while the system is latched comes up unlatched.
- The PID task keeps the Lab 2 calculation on synthetic samples as its workload. With no encoders in this lab, DRIVE applies throttle duty directly.
