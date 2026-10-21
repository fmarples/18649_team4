# Lab 3 Parts 4–5 demo: three zones, dual CAN, N2 relay

The checkoff application for the Lab 3 handout's Part 5, including the Part 4
relay. `lab3_wcet_baseline/` remains the measured Part 3 firmware; this app
reuses its timing instrumentation, PID workload and steering mapping by path
instead of copying them. Pins: [LAB3_PINOUT.md](../doc/LAB3_PINOUT.md#lab-3-part-5-demo-allocation).

**Status:** flashed and deployed on October 21; healthy-bus startup verified (see
[Deployment](#deployment-october-21)). Fault-injection and timing checkoff steps
have not been run.

| Path | Role |
|---|---|
| `stm32_zephyr/` | N2 (front) and N3 (rear) Zephyr app; one build per zone |
| `pi/cockpit.py` | N1 cockpit: UDP → CTRL/BLINK/HB_N1, HB_MON, FORCE_RX, LEDs |
| `tests/test_host.py` | Builds the C zone-state, frame-history and protocol code with host gcc |
| `pi/test_*.py` | Cockpit behavior on python-can virtual buses, plus protocol/state units |

## Design decisions

**Relay (Part 4.2).** Only N2 relays, because only N2 is meant to stay on both
buses. It forwards every CRC-valid first copy whose origin is N1 or N3 to its other
bus **immediately**, unless that bus has already delivered the copy. No fault
detection gates it, so scenario (c) has no 60 ms gap: the first CTRL after the
pulls is relayed like every later one. The cost is that healthy buses also carry
relayed copies. Worst case is about 10 frames per bus per 20 ms, roughly 14 %
utilization against the 50 % limit. This is Tianyi's design from the unmerged
`lab3-relay-immediate` branch; `frame_history.c` is ported from it.

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
`pi/zone_state.py`, holds every threshold. A zone is in error when it is latched,
when a peer zone has had no heartbeat on either bus for 60 ms, or when CTRL (on N1,
UDP) is more than 60 ms old. Power-up therefore starts in error and leaves it once
both peers are heard on some bus and CTRL is fresh. A test-button press, an
out-of-range CTRL or a bad-CRC CTRL latches and sends FAULT. Every receiver latches
on that FAULT. A double press on any zone's button sends FAULT clear, which releases
every latch. FAULT `ZONE_LOST` (reason 4) is informational: each node detects
heartbeat loss itself and recovers without a clear, so restoring an isolated node
returns to normal without a reset.

**Degraded LEDs (R4.7).** DEG_A on a node means it hears no peer heartbeat on A
for 60 ms, after having heard some heartbeat on either bus. Pulling one node's
A jumper lights only that node's DEG_A, because the others still hear each other
on A.

**Outputs.**
- N2 SRV is a 50 Hz servo pulse from the Lab 2 calibrated mapping (1200/1600/2000 µs). In error the pulse stops, which is Lab 2's fault policy.
- N3 PWM_OUT is 10 kHz with duty equal to throttle %, and DIR_A high selects forward.
- Brake or error on N3 drops DIR_A and holds PWM_OUT high: the L298 enable-high/equal-input brake. PWM_SET toggles after each timer write, as in Lab 2.
- Blinkers switch on BLINK reception so both zones change on the same frame. In error the mode is forced to hazard. With no BLINK for 750 ms, an STM32 flashes hazards on its own 500 ms timer.
- The Pi is the blinker master and uses the Lab 2 paddle map (bit 5 left, bit 4 right, steering auto-cancel). It sends BLINK on a change and every 500 ms, all modes at 1 Hz.

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
| Start (Restart while running) / Stop, *Bench input* | `start.py [--restart]` / `stop.py`; asks for the Pi sudo password on each start and passes it on stdin only. Restart redeploys the current `pi/` code and keeps the session's bench setting. *Bench input* adds the laptop sender for use without the wheel | session |
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

From the laptop, in a terminal (it asks once for the Pi sudo password, which is
never stored):

```powershell
python lab3_demo\start.py              # course proxy supplies UDP; add --synthetic for a bench sender
python lab3_demo\stop.py
```

`start.py` checks the can0=spi0.1 / can1=spi0.0 mapping and that GPIO
5/6/12/17/22/23/27 are free. It brings both links up at 500 kbit/s with
`restart-ms 100` if they are down, copies `pi/` to a fresh
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

The wheel A button is N1's test button; single press latches, a double press
clears. Logs go to the session folder (standalone runs default to
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

## Not yet verified

All of the following needs hardware: every checkoff step, both relay directions,
bus-off/reconnect recovery times, the INT re-kick, front/rear blink skew, the
relayed brake chain, and PWM waveforms on PB4.

Known behaviors to watch on hardware:
- Frames queued on a disconnected bus, up to 3 in the MCP2515 or the Pi's txqueue, are sent when the jumper returns. A stale CTRL can be applied for one 20 ms period.
- The latch is carried only by FAULT frames, so a node that reboots while the system is latched comes up unlatched.
- The PID task keeps the Lab 2 calculation on synthetic samples as its workload. With no encoders in this lab, DRIVE applies throttle duty directly.
