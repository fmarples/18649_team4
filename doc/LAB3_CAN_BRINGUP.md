# Lab 3 CAN bring-up verification

Branch: `lab3_can`. Capture date on laptop: 2026-10-19. The Pi's clock differs; correlate remote logs by test, not wall-clock time.

> **HANDOUT ERROR: XIAO CAN module D9 is MISO; D10 is MOSI.** The Lab 3 v1.0 handout reverses these pins. Earlier assistant wiring instructions repeated that error. Use the [manufacturer-verified correction and host pin table](STM32_PINOUT.md#lab-3-handout-erratum-can-module-mosimiso-are-reversed) for all six modules. Preserve the working wiring.

## Current checkpoint status

The user confirmed Parts 0 and 1 fully verified. Software traffic and isolation results are backed by the logs below; completion of the scope checks is user-confirmed. Scope screenshots and waveform exports were not supplied.

| Check | Result | Evidence |
|---|---|---|
| Part 0 development environment | **PASS** (user-confirmed, with live startup evidence) | Both Pi interfaces and all four Nucleo controllers initialized at 500 kbit/s, ERROR-ACTIVE |
| Part 1 termination | **PASS** (user-confirmed 60 ohms on both buses) | User report; no meter capture supplied |
| Part 1 normal traffic from each Nucleo on both buses | **PASS** | Frame captures, sequence checks, MCU/Pi counters below |
| Part 1 single-node bus isolation | **PASS behavior; A/B labels inconsistent** | N2 lost only its connection to Pi can1; the other three streams continued without gaps. See mapping below |
| Part 1 scope checks | **PASS** (user-confirmed) | A transcribed frame decoded with matching CRC. Waveform files were not supplied |

All diagnostic transmitters are stopped. At the end, serial status confirmed `tx=OFF` on both boards, all four controllers ERROR-ACTIVE with TEC=0 and REC=0, and a three-second Pi capture received no frames. N2 controller B retains the historical 267 queue rejects from isolation. Both Pi interfaces remain enabled at 500 kbit/s; no capture process remains. Stop evidence: `logs/lab3-can/20261019-024150-scope-stop-COM4.log`, `20261019-024150-scope-stop-COM6.log`, and `scope-stop-quiet-check.log`.

During the scope session, both senders ran at the user's request: N2/COM4 `lab3 tx 2`, N3/COM6 `lab3 tx 3`, nominal 100 ms frames on both buses at 500 kbit/s. A three-second Pi capture received 30 frames from each sender on each interface. No actuator output was enabled. Evidence: `20261019-021818-scope-start-COM4.log`, `20261019-021818-scope-start-COM6.log`, and `scope-start-traffic.log`.

## Identified firmware and interfaces

Both boards run `LAB3 PART0 dual MCP2515; no automatic TX; no actuators`, Zephyr v4.3.0. Boot output reports 16 MHz crystals, 1 MHz SPI and 500 kbit/s CAN; both controllers report `init_rc=0 ready=1`. The firmware source/build directory has not been located, and no image was flashed during this session.

The diagnostic shell provides `lab3 status`, `lab3 normal`, `lab3 loopback`, `lab3 tx 2`, `lab3 tx 3`, and `lab3 stop`. **TX is off at boot**, explaining the earlier empty captures. The `tx` command starts nominal 100 ms frames on both controllers. This is not the imported demo candidate.

| Test identity | USB port | ST-LINK serial | Diagnostic CAN ID |
|---|---|---|---|
| N2 | COM4 | `066BFF505487525067171333` | `0x701` |
| N3 | COM6 | `066BFF485270535067124020` | `0x702` |

These identities were assigned for the test, not confirmed front/rear mechanical zones. Rediscover USB ports before reuse.

On this Pi boot, `can0` is `spi0.1` / CE1 and `can1` is `spi0.0` / CE0. Interface enumeration is reversed relative to the usual can0/CE0 assumption. The isolation test established the cross-node controller mapping below; firmware A/B labels differ between the Nucleos. The user confirmed both buses connect all three nodes with common ground.

## Normal traffic results

Each sender ran separately with the other Nucleo receiving. The Pi captured both interfaces for a bounded ten-second window, with transmission started after the capture. The observed mean reception interval was approximately 100.804–100.805 ms, rather than exactly 100 ms.

| Sender | Pi can0 frames | Pi can1 frames | Observed interval range across both interfaces |
|---|---:|---:|---|
| N2 / COM4 | 94 | 94 | 100.698–100.914 ms |
| N3 / COM6 | 93 | 93 | 100.696–100.933 ms |

- Payload sequences matched exactly between Pi interfaces, with no gaps or duplicates: N2 counters 0–93, N3 counters 0–92.
- Each Nucleo's RX counters matched the other sender's count on both controllers.
- TX_OK matched the sender capture counts. TEC, REC, TX_ERR, QUEUE_REJECT and RX_DROP were zero on all four MCU controllers.
- Both Pi interfaces ended UP/ERROR-ACTIVE at 500 kbit/s with 187 received packets each and zero displayed errors/drops.
- Both periodic senders were explicitly stopped and confirmed `tx=OFF`. All serial monitors/captures exited; no `candump` process remained. Both Pi interfaces remain up in normal mode.

This passes normal Part 1 traffic. The subsequent isolation result is below; the user later confirmed scope checks and Part 1 complete. No actuator tests were performed.

### Evidence

Local persistent files under `logs/lab3-can/`:

- `20261019-015556-COM4-boot.log`, `20261019-015556-COM6-boot.log`
- `20261019-015659-N2-candump.log`, `20261019-015659-N3-candump.log`
- `20261019-015659-N2-summary.json`, `20261019-015659-N3-summary.json`
- `20261019-015659-sequence-check.log`, `20261019-015659-pi-final.log`
- `20261019-015726-COM4-commands.log`, `20261019-015727-COM6-commands.log`

Raw logs are local and ignored by Git; this document records the team verification result. Preserve command errors and Python crash tracebacks beside captures. Scope captures must identify the bus and channels.

## Single-node isolation and reconnection

With both senders running, the user removed one Nucleo's intended bus-A isolation jumper and left termination in place. The affected node was N2 / COM4, firmware controller B. A roughly 64.38-second recording captured baseline traffic, disconnection and the isolated state.

| Stream seen at Pi | Result |
|---|---|
| can1 / N2 `0x701` | Stopped after 354 captured frames, approximately 35.585 seconds after the first frame |
| can0 / N2 `0x701` | Continued until deliberate stop; 622 frames, no sequence jumps, maximum interval 100.853 ms |
| can1 / N3 `0x702` | Continued until deliberate stop; 631 frames, no sequence jumps, maximum interval 100.842 ms |
| can0 / N3 `0x702` | Continued until deliberate stop; 631 frames, no sequence jumps, maximum interval 100.918 ms |

The lost stream was absent for the final approximately 28.8 seconds of traffic. This verifies that the isolated node continued on the other bus and the affected bus still carried traffic between the remaining Nucleo and Pi. No exact disconnect-to-detection latency is claimed; the physical action was not instrumented.

**Bus labels are inconsistent across nodes.** The traffic and MCU RX/TX counters establish:

| Physical shared bus, identified by Pi | N2 / COM4 firmware label | N3 / COM6 firmware label |
|---|---|---|
| can0 / CE1 | CAN A | CAN B |
| can1 / CE0, disconnected in this test | CAN B | CAN A |

Reconcile the bus labels/wiring plan before later relay and per-bus fault tests. Do not assume that firmware CAN A denotes the same physical bus on both Nucleos. This test did not change the wiring plan beyond removing and restoring the single isolation jumper.

The isolated N2 controller B entered ERROR-PASSIVE, with REC=135 and 267 queue rejects; these belong to the disconnected path, not the surviving streams. After both periodic senders were stopped, the user restored the jumper. A new bounded traffic run recovered all four streams **without a board reset, firmware change, or controller-mode reset**:

- N2: 98 captured frames per Pi interface; N3: 89 per interface.
- Per-sender payload sequences matched between interfaces with no sequence gaps; maximum observed interval across all four streams was 100.929 ms.
- All four MCU controllers ended ERROR-ACTIVE. N2 B retained REC=29 and the historical 267 queue rejects; TEC was zero. Other MCU error counters remained zero. No claim of cleared historical errors is made.
- Both Pi interfaces remained ERROR-ACTIVE with zero displayed errors/drops.
- Both periodic senders were stopped and confirmed `tx=OFF`; serial/capture processes exited. Both Pi interfaces remain up, and the user confirmed the jumper restored.

Reconnection timing was not measured. This is a Part 1 connectivity test, not proof of Lab 3 fault-detection/recovery deadlines or bus-off recovery.

Evidence under `logs/lab3-can/`:

- `20261019-015941-isolation-candump.log`, `20261019-015941-isolation-summary.json`
- `20261019-015941-isolation-COM4.log`, `20261019-015941-isolation-COM6.log`
- `20261019-015941-isolation-monitor.log`, `20261019-015941-isolation-pi-final.log`
- `20261019-020358-reconnected-candump.log`, `20261019-020358-reconnected-summary.json`
- `20261019-020358-reconnected-COM4.log`, `20261019-020358-reconnected-COM6.log`, `20261019-020358-reconnected-pi-final.log`

## User-supplied scope bit sequence

While scope traffic was running, the user supplied a 111-bit sequence. Interpreting the supplied `1` as CANH high voltage, inverting to CAN logical polarity, and removing stuff bits yields a standard data frame:

- ID `0x701`, RTR=0, IDE=0, reserved bit=0, DLC=8.
- Data `25 1B 00 00 02 00 00 00`, consistent with N2 diagnostic counter 6949 and node ID 2.
- Received CRC-15 `0x2C66` equals the computed CAN CRC-15 using polynomial `0x4599`.
- The last two supplied bits decode as CRC delimiter=1 and ACK slot=0. The ACK delimiter and EOF are not included.

The user confirmed their bit reading was reversed and reported that the waveform stayed flat after the final pulse. The transcribed sequence excludes the flat ACK-delimiter/EOF interval; that does not establish that the scope capture itself omitted it. The calculated complete frame length is 119 bits including stuffing, or 238 us at the configured 500 kbit/s, followed by at least 6 us intermission. This duration is calculated, not an independently measured scope result.

The user subsequently confirmed Part 1 fully verified. The bit string and decode are retained in `logs/lab3-can/user-scope-bitstring-analysis.log`; waveform screenshots/exports, channel/bus labels and measured time scales were not supplied. Record the scope completion as user-confirmed rather than independently inspected. Scope transmission was subsequently stopped for the final state recorded at the top of this document.

## Troubleshooting history and corrected conclusions

1. Initially only one Nucleo enumerated; both later appeared. Passive six-second console captures were empty. Capturing both boards during user-triggered resets revealed the diagnostic shell above.
2. The Pi initially had both interfaces down. `can1` started, but `can0` timed out entering normal mode. The user measured approximately 2 V on the affected module's supply, CANH and CANL, found a loose wire, and later confirmed 3.3 V supply. Post-correction CANH and CANL were approximately 2.28 V each.
3. Linux accepted `can0` loopback mode, but a subsequent actual internal-frame test failed: no controller RX and no completed TX. Merely accepting loopback mode was **not** evidence clearing SPI/controller/interrupt connections. The diagnostic used ID `0x7A5`, payload `T4LOOP01`, rejected SocketCAN local TX echo as proof, and restored normal-mode configuration afterward.
4. The assistant repeated the handout's incorrect MOSI/MISO mapping. After that swap, both controllers failed probing with `MCP251x didn't enter in conf mode after reset`, error -110. Explicit reprobes reproduced the failure.
5. The user restored the previous arrangement, and both Pi controllers started successfully. The user identified the handout error; Seeed's manufacturer schematic and XIAO pin documentation confirm **D9=MISO, D10=MOSI**. The corrected mapping is in the pin document, hardware document, both Lab 3 READMEs and AGENTS.md.
6. Once the diagnostic's explicit transmit commands were used, normal traffic passed as recorded above. No firmware replacement was necessary.
7. At the user's request, both senders were later restarted for oscilloscope work and then stopped. The scope session added a transcribed frame with a matching CRC but no saved waveform export.

Historical logs include `can0-mode-diagnostic.log`, `can0-loopback-frame.log`, `pi-spi-interrupts.log`, `confirmed-3v3-retry.log`, `after-spi-correction-probe.log`, `after-spi-correction-reprobe.log`, and `after-swapped-back.log`. The early `candump -L -e` attempt failed because its flags are incompatible; subsequent captures used valid options. A capture against a down interface also exited immediately and was not counted as an observation window.
