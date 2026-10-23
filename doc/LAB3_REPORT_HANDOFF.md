# Lab 3 report handoff (October 23)

What has been measured for the Lab 3 write-up, where the photos are, and what is
still open. Rules come from the [Lab 3 handout](18-449_649%20Lab%203%20-%20Dual-CAN%20v1_0.pdf)
and the [October 22 student clarification](18-449_649%20Lab%203%20-%20Student%20clarification%202026-10-22.pdf),
which overrides the handout where they differ. Full measurement ledger, rejected
photos and per-photo notes: [LAB3_TIMING_RESULTS.md](LAB3_TIMING_RESULTS.md#demo-build-clarification-measurements-16-october-23).

## Report checklist

| Report item (handout Deliverables) | Points | Status |
|---|---:|---|
| Wiring schematic: both buses, termination, every module's SPI/INT/CS, test-point boards | 6 | **Open.** Inputs ready, see [Schematic inputs](#schematic-inputs) |
| Task communication graph with the four chains highlighted | 8 | **Open.** Inputs in [Task set](#task-set-and-priorities) |
| Single-bus analysis: N2/N3 RTA tables, CTRL message RTA, chain table, measured Pi latency | 10 | **Measurements done** (#1–#4). Tables open |
| Dual-bus and relay analysis: RELAY in the graph, relay design, re-analysis for scenario (c), verdict per chain | 10 | **Measurements done** (#5, #6). Tables open; design notes below |
| Fault-injection matrix (R4.8 a–f): expected state of each zone and LED, measured recovery time | 4 | **Measured.** All six scenarios; table below |
| Updated team-defined values table and Lab 1 revision history | 2 | **Open** |

The report is at most six pages, excluding the schematic and scope captures. Every
WCET or latency must say whether it is measured or assumed, and how it was measured.

## The six required scope measurements

All on the flashed `lab3_demo` app with Logitech wheel traffic. Scope: Agilent
DSO7012B. Report the **Max**. Each photo shows both probes and the statistics row.

| # | Quantity | Max | Boundary (start → stop) | Photo(s) for the report |
|---|---|---:|---|---|
| 1 | Pi stage (CTRL's J) | **995 µs** | N1 UDP_RX rising → CMD_TX rising, after the first CAN write returns | [IMG_0893](lab3-scope/demo-1-pi-stage-wheel-IMG_0893.jpg) |
| 2 | CAN_RX C, N3 | **202.0 µs** | CAN A module INT falling (PA10) → CAN_RX_A toggle | [IMG_0897](lab3-scope/demo-2-n3-can-rx-rise-IMG_0897.jpg) (rising toggles, 201.0), [IMG_0900](lab3-scope/demo-2-n3-can-rx-fall-IMG_0900.jpg) (falling toggles, 202.0) |
| 3 | DRIVE C, N3 | **89.4 µs** | CAN_RX_A toggle → DIR_A falling on a brake frame | [IMG_0903](lab3-scope/demo-3-n3-drive-IMG_0903.jpg) |
| 4 | SPI frame load B | **80.2 µs** | N3 CAN A module CS low width (PB6), longest window | [IMG_0905](lab3-scope/demo-4-n3-spi-cs-IMG_0905.jpg) |
| 5 | CAN_RX C, N2 | **201.5 µs** | CAN A module INT falling (PB5; N2 is the `swap_ab` board) → CAN_RX_A toggle | [IMG_0906](lab3-scope/demo-5-n2-can-rx-IMG_0906.jpg) |
| 6 | RELAY C, N2 | **963 µs** | CAN_RX_A toggle on N2 → RELAY_TX toggle after the bus-B send returns; N1 off B, N3 off A | [IMG_0909](lab3-scope/demo-6-n2-relay-IMG_0909.jpg) |

How each was taken, for the "how measured" sentences:

- **Toggles:** STM32 test points are C GPIO writes (a few µs). Pi test points are
  Python libgpiod writes (tens of µs). The STM32s send with a TX callback, so no
  pulse includes time on the wire.
- **Keeping other tasks idle (clarification):**
  - #2 and #5: the measured node's application transmits were paused
    (`timing tx off`) and the node was unplugged from bus B.
  - #3: the node was unplugged from bus B.
  - #6: N3's transmits were paused, so RELAY_TX marked only N1's frames
    relayed onto B.
- **Edge pairing:** the scope's Delay measurement pairs the edges nearest the
  trigger and measures only what is on screen. Every capture triggers on the stop
  edge, with the screen just wider than the expected interval.
  - #2, #3 and #5 cover both toggle polarities. #2 has one photo per polarity;
    #3 and #5 measure both at once.
  - Rejected and superseded photos are listed in the ledger.
- **#1 timing:** the Pi ran the cockpit at SCHED_FIFO priority 1 on the stock
  (non-PREEMPT_RT) kernel, with UDP over Wi-Fi. A synthetic-sender run reached
  1885 µs ([IMG_0892](lab3-scope/demo-1-pi-stage-IMG_0892.jpg), supplementary).
  State which run you use and why.
- **#6 cross-check:**
  - The scope's Mean/Min on IMG_0909 are not meaningful. Relays overlap, so some
    edges pair with the wrong frame; use only the Max.
  - N2's firmware cycle counter measured the same boundaries per relayed frame
    and found 940 µs over about 20,000 relays. Log:
    `logs/lab3-can/20261023-095456-demo-build-relay-c-timer2/console-130s.log`.
  - Long relays are waits for one of the MCP2515's three bus-B TX buffers,
    behind N2's own heartbeat/FORCE frames and earlier relays.
- **SPI:** SPI1 runs at 5.25 MHz (84 MHz / 16) in polling mode.

## Using the numbers in the RTA

- **B:** use #4, **80.2 µs**, counted once per task. `send_both()` holds no lock
  across the two buses: the MCP2515 driver takes the shared SPI bus only for each
  transaction. B is 0 for the lowest-priority task.
- **Measured C values:**
  - N3: CAN_RX 202.0, DRIVE 89.4.
  - N2: CAN_RX 201.5, RELAY 963.
  - Every other task uses the clarification's placeholder C.
- **CTRL message:** J = #1 = 995 µs. CTRL has the highest priority ID, so
  R = J + 270 + 270 = **1535 µs**.
- **Relayed CTRL on B:** J = Pi (#1) + CTRL on A (540) + CAN_RX R (N2) + RELAY R
  (N2), using the R values from your N2 table.

### Brake-chain verdicts (measured-input sums; RTA terms only add)

| Chain, deadline 2 ms | Sum | Verdict |
|---|---:|---|
| Direct: Pi 995 + CTRL on A 540 + CAN_RX N3 202 + DRIVE 89 | ≈ 1826 µs | Borderline; check against your R values |
| Relayed (scenario c): Pi 995 + CTRL on A 540 + CAN_RX N2 202 + RELAY 963 + CTRL on B ≥ 540 + CAN_RX N3 202 + DRIVE 89 | ≈ 3531 µs | **Misses** |

The clarification allows a miss if you mark it, say why, and say what would fix
it. Wording ready to adapt:

- **Why it misses:** the two CAN hops (≥ 1080 µs) and the Pi's worst case
  (995 µs) together exceed 2 ms before any MCU work, so the chain misses even
  with a zero-time relay (≈ 2568 µs). The Pi tail is Linux scheduling
  (typical 310 µs). RELAY's tail is TX-buffer waiting.
- **What would fix it:** both changes are needed, giving a Pi stage of about
  300 µs or less and RELAY of about 130 µs or less.
  - A bounded Pi stage: PREEMPT_RT kernel, an isolated CPU, or a C cockpit.
  - A reserved MCP2515 TX buffer, or the chip's TX priority bits, for relayed
    frames, so RELAY stays near its 160–200 µs base.

## Relay design (for the defense section)

- **Who relays:** only N2. N1 and N3 never forward.
- **When it relays:** N2 forwards a frame from N1 or N3 to the other bus only
  when it has heard no heartbeat from that sender on the destination bus for
  60 ms. This is the handout's "forward only when it detects that a bus is
  degraded" option.
  - Healthy buses carry no relayed copies; measured: 0 relays, every frame
    gated.
  - The first relayed CTRL after a pull can be 60–80 ms late. No zone treats a
    stale CTRL as an error, so the system stays up through that gap.
- **Why it waits for the sender to be absent:** the first version relayed
  immediately.
  - With N3 off bus B, only the Pi and N2 remained there. N2's copy of a Pi frame
    sometimes started on the same bit as the Pi's own copy.
  - A CAN frame is acknowledged by a node that isn't sending, and identical
    simultaneous frames don't collide. With no third node, neither copy was
    acknowledged, so both retried in lockstep until bus B jammed.
  - This was found and fixed on October 23. See the design note in the
    [demo README](../lab3_demo/README.md#design-decisions).
- **Loops and duplicates:**
  - N2 makes at most one forwarding attempt per (ID, source, sequence number)
    per destination bus.
  - Every node drops copies of its own frames.
  - Receivers drop any (ID, source, seq) already seen within 20 ms on either bus.
- **Priority:** RELAY is priority 2 on N2: below RX dispatch (1), above STEER (3).
  The MCP2515 driver threads are cooperative and run above all of them.
- **Bus utilization in scenario (c):** relayed frames to list, starting from the
  clarification's 8.6 % and adding 1.35 % per extra frame every 20 ms.
  - Onto B: CTRL (20 ms), HB_N1 (20 ms), BLINK (500 ms periodic; minimum
    interval 20 ms), FAULT (event-driven; minimum interval 20 ms).
  - Onto A: HB_N3 (20 ms), FAULT.
  - N2's own HB_N2 and FORCE are sent on both buses anyway; they are not relays.
  - Worst case is about 14.0 % on B and 11.3 % on A, both under 50 %. Check this
    arithmetic before using it.

## Task set and priorities

From `lab3_demo/stm32_zephyr/src/main.c`. In Zephyr a lower number runs first;
the MCP2515 driver's interrupt/RX threads are cooperative and run above all of these.

| Priority | N2 (front) | N3 (rear) |
|---:|---|---|
| 1 | RX dispatch (CAN_RX) | RX dispatch (CAN_RX) |
| 2 | RELAY, BLINK_F | BLINK_R |
| 3 | STEER | DRIVE |
| 4 | TEST_BTN | TEST_BTN |
| 5 | – | PID |
| 6 | HB_MON | HB_MON |
| 7 | HB_TX | HB_TX |
| 8 | FORCE_TX | – |

## Fault-injection matrix

**Recovery time** is measured from the first frame received after the jumper
is restored (the node's CAN_RX toggle) to its DEG/ERR LED clearing. Captures
use single-shot mode with cursors. The LEDs are re-evaluated when a CTRL frame
arrives or at the 20 ms HB_MON tick, not on every frame, so restore times range
from tens of µs to about 20 ms.

| Scenario | Expected state | Observed | Recovery time |
|---|---|---|---:|
| (a) one node off A (N3 tested) | That node DEG_A on; nothing else changes; no ERR, no hazards | Matches. DEG_A on 60.6 ms after the last frame ([IMG_0912](lab3-scope/matrix-a-n3-pull-deg-a-IMG_0912.jpg)) | **14 ms** ([IMG_0910](lab3-scope/matrix-a-n3-restore-deg-a-IMG_0910.jpg)) |
| (b) one node off B (N3 tested) | That node DEG_B on; nothing else changes | Matches. DEG_B on 60.4 ms after the last frame ([IMG_0913](lab3-scope/matrix-b-n3-pull-deg-b-IMG_0913.jpg)) | **1.8 ms** ([IMG_0914](lab3-scope/matrix-b-n3-restore-deg-b-IMG_0914.jpg)) |
| (c) N1 off B, N3 off A | N1 DEG_B, N3 DEG_A, N2 no DEG; no ERR; RELAY_TX toggling on N2; N3 follows the wheel through the relay | Matches. N2 relayed about 9,750 frames with one failure and stopped after the restore | **2.2 ms** for N3's DEG_A ([IMG_0919](lab3-scope/matrix-c-n3-restore-deg-a-IMG_0919.jpg)) |
| (d) one STM32 off both buses (N3 tested) | Isolated node in fail-safe within 100 ms (N3: DIR_A low, PWM_OUT held high, hazards, ERR on). The other two in system error (ERR on, hazards). No DEG LEDs on the other two (they still hear each other) | Matches. N2 ERR rose at most **74.4 ms** after N3 was cut off ([IMG_0920](lab3-scope/matrix-d-n3-isolated-n2-err-IMG_0920.jpg)) | **≈ 18 ms**, no reset. N2 cleared before N3 received anything (N3's queued frames go out on contact; [IMG_0921](lab3-scope/matrix-d-restore-n2-err-first-IMG_0921.jpg)). N3's own ERR cleared 17.6 ms after its first received frame ([IMG_0922](lab3-scope/matrix-d-restore-n3-err-IMG_0922.jpg)) |
| (e) every node off A | DEG_A on all three; system fully operational on B; no ERR | Matches (console and cockpit state) | **3.2 ms** when bus A came back: N3 plugged in first, then N2 ([IMG_0918](lab3-scope/matrix-e-n3-bus-a-back-IMG_0918.jpg)) |
| (f) restore any jumper | Normal operation within 500 ms, no reset; DEG off within 100 ms | Every restore above; a second (a) sample cleared in 43 µs ([IMG_0916](lab3-scope/matrix-a-n3-restore-zoom-IMG_0916.jpg)) | worst measured ≈ 18 ms |

Open risk, not observed: if the Pi and N2 rejoin bus A while N3 is still off it, N2 may relay a Pi frame onto A during the first heartbeat period, before it hears the Pi there. Two nodes sending identical frames get no acknowledgment and can jam the bus, as the immediate relay did. Restoring jumpers in a different order avoids it; a firmware guard is not implemented.

## Schematic inputs

- **Pins:**
  - Module SPI/CS/INT for every module, the MOSI/MISO erratum and the Pi pins:
    [LAB3_PINOUT.md](LAB3_PINOUT.md).
  - Test-point boards, physical pin to breadboard row:
    [lab3-testpoint-wiring.html](lab3-testpoint-wiring.html) (open in a browser).
- **Bus labels:** bus A is Pi can0. N2 is built with `swap_ab`, because its CS
  PB6/INT PA10 module is wired to bus B.
- **Termination:** the team reports two discrete 120 Ω resistors per bus on the
  breadboard and one wire pair from each module's screw terminal to the rails.
  Before submitting, confirm that every module's P1 pad is open and state it.
  The clarification asks you to list any terminated module.
- **Ground:** draw the common ground between the Pi, both Nucleos and the bus
  breadboard.

## Lab 1 revision-history items from this lab

- N2 relays only toward a bus where the sender is absent for 60 ms. It
  previously relayed immediately; that version jammed two-node buses.
- Measured Pi stage, SPI frame load and RELAY C replace the placeholders.
- Hazards at 1 Hz and no UDP force message: where Lab 1 and Lab 3 conflict, the
  team follows Lab 3. See the demo README's spec-alignment section.

## Firmware and evidence

- **N2** (ST-LINK ending 124020): `logs/lab3-can/20261023-095456-demo-build-relay-c-timer2/`.
  This is the relay gate plus the RELAY C counter on the console, and matches the
  committed source.
- **N3** (ending 171333): the 05:15 build `logs/lab3-can/20261023-051503-demo-build-spec/`.
  Today's source changes affect N3 only through an unused function and struct
  field, so its behavior matches the committed source.
- **Photos:** original photos are in `logs/lab3-can/20261023-demo-scope/`
  (local only, not in Git). The resized copies linked here are in `doc/lab3-scope/`.
