# Lab 3 CAN bring-up verification

Branch: `lab3_can`. Capture date on laptop: 2026-10-19. The Pi's clock differs; correlate remote logs by test, not wall-clock time.

> **HANDOUT ERROR: XIAO CAN module D9 is MISO; D10 is MOSI.** The Lab 3 v1.0 handout reverses these pins. Earlier assistant wiring instructions repeated that error. Use the [manufacturer-verified correction and host pin table](STM32_PINOUT.md#lab-3-handout-erratum-can-module-mosimiso-are-reversed) for all six modules. Preserve the working wiring.

For the current selected results and remaining coverage, see [LAB3_TIMING_RESULTS.md](LAB3_TIMING_RESULTS.md). The entries below are chronological; earlier pending/running states are historical, not current operating instructions.

## Completed diagnostic SPI/interrupt measurement session after Part 1

Both diagnostic senders were restarted for the user's SPI timing measurement at laptop time 2026-10-19 02:57. Both confirmed normal mode and `tx=ON`; a three-second Pi capture received 30 frames from each sender on each interface. For the initial captures, both boards transmitted. The subsequent user-triggered reset identified the probed board as COM6 / ST-LINK ending `124020`; COM6 then operated receive-only while COM4 continued nominal 100 ms test transmission on both buses. At the end of this session, both boards were confirmed `tx=OFF`; a three-second Pi capture was quiet, and all capture processes exited. No firmware was changed. The user connected scope probes to Nucleo D10/PB6 and D13/PA5. Photos establish CH1/yellow as SCK and CH2/green as CS. The scope is an Agilent InfiniiVision DSO7012B. A subsequent cursor capture at 1 us/div showed 1.520 us between consecutive SCK rising edges, approximately 658 kHz, despite the firmware's requested SPI frequency of 1 MHz. Treat this as an observed clock period, not proof of the actual peripheral-divider setting. A later capture measured an approximately 202.5 us CS-low interval for one longer SPI transaction; details below. Evidence: `logs/lab3-can/spi-clock-IMG_0826.JPG`, copied from the user-supplied photo. The later reset identification established the probed board as COM6 / ST-LINK ending `124020`.

Evidence: `logs/lab3-can/20261019-025722-spi-scope-start-COM4.log`, `20261019-025722-spi-scope-start-COM6.log`, and `spi-scope-start-traffic.log`. Receive-only phase status evidence: `logs/lab3-can/20261019-033844-rx-only-COM4.log` and `20261019-033844-rx-only-COM6.log`. The reset capture is `20261019-033530-identify-probe-COM6.log`. The diagnostic defaults its printed node identity to N2 after reset; the physical COM6 board remains the board previously assigned N3 for tests. Final stop evidence for this measurement session: `logs/lab3-can/20261019-035352-spi-scope-stop-COM4.log`, `20261019-035352-spi-scope-stop-COM6.log`, and `20261019-035352-spi-scope-stop-quiet.log`. All four controllers remained ERROR-ACTIVE with TEC/REC zero; COM4 controller B retained its historical 267 queue rejects. Pi interfaces remain enabled. The older stop evidence below describes the end of the earlier Part 1 session.

### SPI requested frequency versus measured clock

| Quantity | Value | Evidence type |
|---|---|---|
| Requested SPI frequency | 1,000,000 Hz | Diagnostic boot/status output; both imported starter overlays specify `spi-max-frequency = <1000000>` |
| Measured SCK period | 1.520 us | Scope time cursors between consecutive rising edges in `spi-clock-IMG_0826.JPG` |
| Frequency calculated from measured period | Approximately 658 kHz | `1 / 1.520 us`; limited by cursor placement and scope accuracy |
| Predicted clock with default board settings | 656.25 kHz, period 1.52381 us | Default 84 MHz SPI1 source divided by 128; not a readback of the running registers |

The installed Zephyr v4.3.0 STM32 SPI driver, `drivers/spi/spi_ll_stm32.c`, selects the fastest power-of-two divider whose result does not exceed the requested frequency. With the board's default 84 MHz SPI1 clock, divide-by-64 gives 1.3125 MHz, exceeding the request; divide-by-128 gives 656.25 kHz. This closely matches the scope observation. The running diagnostic's source/build and divider register have not been inspected, so retain the distinction between measured period and inferred configuration.

The 1 MHz request is an inherited setting, not a handout requirement or a documented timing-derived choice. Its original rationale is unknown. The user chose to retain this configuration for the current measurement session and record the contrast. No clock setting was changed. These SPI measurements do not change the independently configured 500 kbit/s CAN bitrate. Final application timing results must identify their SPI configuration and be repeated if that configuration changes.

### Observed SPI transaction duration

The user supplied `IMG_0829.JPG`, retained as `logs/lab3-can/spi-cs-width-IMG_0829.JPG`. With CH1=SCK, CH2=CS, 50 us/div and a CH2 duration trigger at 1.50 V, the displayed time-cursor separation was **202.50000 us** across the selected CS-low interval. Record approximately **202.5 us** as one observed transaction's CS-low duration, including clock gaps and CS setup/hold. The scope cursor sources were CH1, but the time cursors visually align with the green CS boundaries; their displayed CH1 voltages are not CS measurements.

This is not a proven maximum, pure CPU execution time, or complete CAN-receive response time. Both Nucleos were transmitting, so without the SPI command byte the selected transaction is not identified as a receive-buffer read versus a transmit-buffer load. The later reset identification established that these probes were on COM6 / ST-LINK ending `124020`. After the repeated-duration measurement instructions, the user reported a displayed maximum of **202 us**. No statistics screenshot, count, minimum or mean was supplied. This is consistent with the earlier approximately 202.5 us cursor measurement; retain 202.5 us as the largest recorded observation rather than rounding it down to the reported integer maximum. Neither measurement establishes a formal worst-case bound.

### Observed receive interrupt-to-first-SPI delay

On the receive-only COM6 board, the user moved CH1 to Nucleo D2/PA10 (the selected module's INT) and retained CH2 on D10/PB6 (CS). COM4 continued nominal 100 ms diagnostic transmission on both buses. In `logs/lab3-can/int-to-spi-IMG_0834.JPG`, the time cursors span the yellow INT falling edge to the first following green CS falling edge, displaying **76.00000 us**. Record approximately **76 us** for this observed interrupt-to-first-SPI-access delay. Both cursor sources were CH2, but the time placements identify the two different signal edges; the voltage readouts do not measure INT. The screenshot shows a CH1 falling-edge trigger at 3.30 V; lower it to approximately 1.5 V for subsequent captures.

This elapsed delay may include interrupt handling, deferred-driver scheduling, preemption and SPI-resource waiting. It is not isolated ISR CPU execution, complete receive processing, or a proven maximum. SPI opcode decoding and driver timing instrumentation have not yet established which operations follow the first access.

### Observed interrupt assertion duration

In `logs/lab3-can/int-low-width-IMG_0836.JPG`, the same receive-only COM6 setup shows a **336.00000 us** cursor separation spanning the yellow INT falling and rising edges. Record approximately **336 us** as one observed INT-low duration. The scope is at 100 us/div, CH1 falling-edge trigger at 1.50 V. Both cursor sources remain CH2; the time positions identify the yellow edges, while the displayed voltage values belong to CS. The green trace shows two CS-low intervals during this assertion.

This measures the controller's interrupt assertion duration, not a task's CPU execution or necessarily completion of application receive processing. It already includes the interrupt-to-first-SPI interval; do not add the separately observed 76 us to 336 us. It also overlaps SPI transfer time. These are separate captures, not an exact additive timing decomposition.

The subsequent photo `logs/lab3-can/int-low-stats-IMG_0838.JPG` shows automatic CH1 negative-width statistics: **count 254**, current/minimum/maximum **336 us**, and mean **336.00 us**. Record **336 us as the displayed observed maximum across 254 scope measurements**, not a proven worst-case bound. The actual collection duration was not independently verified. Equal displayed values do not establish zero jitter or sub-resolution accuracy; the displayed approximately attosecond-scale standard deviation is numerical residue, not meaningful physical precision.

These results characterize the existing non-actuating Part 0 diagnostic. Application task WCET, complete CAN receive processing, mutex blocking bounds and Pi command latency remain unmeasured.

## Current checkpoint status

The user confirmed Parts 0 and 1 fully verified. Software traffic and isolation results are backed by the logs below; completion of the Part 1 scope checks is user-confirmed. Part 1 CAN-waveform screenshots and waveform exports were not supplied; the later SPI/interrupt scope photos are recorded above.

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


## October 19 measurement-firmware deployment

The user explicitly waived diagnostic backup. Wiring, the requested 1 MHz SPI
clock and measurement-only scope remain unchanged. No valid diagnostic recovery
image was obtained; attempted readbacks must not be used for restoration.

Both measurement images were deployed through serial-matched ST-LINK storage:
N2 `066BFF505487525067171333` (COM4/D:) and
N3 `066BFF485270535067124020` (COM6/E:). Ports were rediscovered before use.
The first image restarted repeatedly because the STM32 watchdog driver installed
its boot timeout before the app installed its own (`-ENOMEM`). The corrected
configuration uses `CONFIG_WDT_DISABLE_AT_BOOT=y`; main still installs and feeds
the application's watchdog. Both rebuilt images reached their correct online
banner, each emitted 54 OBS_TASK records in the startup capture, and reported
zero TX rejects/completion failures in those captures. No FAIL.TXT was present.

The deployed archive is `logs/lab3-can/20261019-043636-measurement-build/`,
including sources, binaries, matching ELFs, configurations and hashes. The earlier
042029 archive contains the watchdog-conflicting image and is not the deployed
version. N2 SHA-256:
`6f8d24cef7e664fb3a214caae37253bfb400531f1aa24cbca569ec3ee15a80e6`;
N3: `702e6f5d92b0a484c047d772620480d745116f0dcf215c7c1053f97d39f821a8`.

A three-second Pi capture received 150 frames each of IDs 0x101 and 0x102,
and 60 frames of 0x300, on **each** bus. COM6 accepted `timing probe hb_tx`
and `timing probe off`; selection was left off. PC8/CN10-2 is not yet physically
probed. Firmware now transmits automatically; the old diagnostic's TX-off state
and `lab3 stop` commands no longer apply. No Pi bridge was started; bounded
candump exited. Physical timing, fault-injection, actual actuator workloads and
Pi idle/stress latency remain unmeasured.

Persistent evidence (Git-ignored):
- `logs/lab3-can/20261019-043803-measurement-flash-n2-COM4.log`
- `logs/lab3-can/20261019-043803-measurement-flash-n3-COM6.log`
- `logs/lab3-can/measurement-deployment-latest.json`
- `logs/lab3-can/measurement-firmware-traffic.log`
- `logs/lab3-can/measurement-probe-command.log`
- `logs/lab3-can/measurement-host-tests-after-flash.log`

The complete serial logs are also the crash-report location; retain any logged
coredump with the matching archived ELF. No crash dump was observed in the
successful startup captures, and coredump behavior remains untested.

The user confirmed moving CH1 to PC8/CN10-2 with CH2 unchanged. After USB reconnection, N3 accepted `timing probe hb_tx`; selection is active until reset or changed. Serial evidence: `logs/lab3-can/20261019-044731-n3-hb-tx-probe.log`. Physical pulse shape/width is not yet verified.


### Selected N3 heartbeat-task scope result

The user selected the later, freshly reset statistics capture IMG_0841 as the
reported result, superseding the earlier request to report both capture windows.
The earlier capture is excluded from the selected result. Firmware, wiring and
the requested 1 MHz SPI clock are unchanged. CH1 is PC8 with `timing probe hb_tx`;
CH2 remains CAN A CS PB6. The scope was stopped for the photograph.

- Current 790 us; mean 789.49 us; minimum 785 us; maximum 790 us.
- Displayed standard deviation 1.5095 us; count 1.618k.
- Horizontal 500 us/div; CH1 1 V/div; rising-edge trigger at 1.50 V.
- A 60-second collection was requested; duration was not independently verified.
- Photo: `logs/lab3-can/hb-tx-stats-IMG_0841.JPG`.

This is task-body elapsed pulse width for this capture window, including waits
and preemption within the body, not isolated CPU execution or a proven WCET.
Its scale is consistent with the earlier serial HB_TX maximum of 813 us, but
those counters cover a different window and slightly different boundaries.
Selecting this capture does not establish the cause of the earlier variability.

Next task selected: N3 `timing probe hb_mon`, accepted on COM6. PC8/CH1 and CS/CH2 wiring unchanged. Scope measurement pending. Serial evidence: `logs/lab3-can/20261019-045540-n3-hb-mon-probe.log`.

### N3 heartbeat-monitor scope observation

The user reported consistently 19 us minimum, mean and maximum and chose to proceed to the next task. No photograph, measurement count or collection duration was supplied for this observation. It is elapsed task-body pulse width at the displayed scope resolution, not a demonstrated WCET or proof of zero jitter.

Next task selected: N3 `timing probe rx_dispatch`, accepted on COM6. PC8/CH1 and CS/CH2 wiring unchanged. Scope measurement pending. Serial evidence: `logs/lab3-can/20261019-045921-n3-rx-dispatch-probe.log`.


### N3 CAN receive-dispatch scope result

CH1 PC8 selected `rx_dispatch`; CH2 remained CAN A CS PB6. IMG_0843 shows:

| Statistic | CH1 positive pulse width |
|---|---:|
| Current | 24 us |
| Minimum | 21 us |
| Mean | 23.503 us |
| Maximum | 24 us |
| Standard deviation | 1.1163 us |
| Count | 965 |

Horizontal 100 us/div; CH1 1 V/div; rising-edge trigger at 1.50 V.
The photo shows acquisition running. Collection duration was not independently
verified. Evidence: `logs/lab3-can/rx-dispatch-stats-IMG_0843.JPG`.

Selected scope maxima so far: N3 heartbeat TX 790 us, heartbeat monitor 19 us
(user report), and receive dispatch 24 us. Keep detailed measurement boundaries
in this document; user-facing bench updates should report the evidence directly
without repeating the same maximum/WCET caveat at every step.

Next task selected: N3 `timing probe blink`, accepted on COM6. PC8/CH1 and CS/CH2 wiring unchanged. Scope measurement pending. Serial evidence: `logs/lab3-can/20261019-050157-n3-blink-probe.log`.

### N3 blinker scope observation

The user reported 15 us minimum, mean and maximum for the selected BLINK task. No photo, count or duration was supplied. Selected scope maxima are now HB_TX 790 us, HB_MON 19 us, RX_DISPATCH 24 us and BLINK 15 us.

Next task selected: N3 `timing probe pid`, accepted on COM6. This measures the current 10 ms PID-demo worker, not the Lab 2 motor-control algorithm. Probe wiring unchanged. Scope measurement pending. Serial evidence: `logs/lab3-can/20261019-050430-n3-pid-probe.log`.

### N3 PID-demo scope observation

The user reported a consistent 11 us pulse for the selected PID-demo worker. Selected measured maximum: 11 us. No photo, count or duration was supplied. This is the existing demo worker, not the Lab 2 motor PID implementation.

Next task selected: N3 `timing probe test_btn`, accepted on COM6. The worker is interrupt-driven and has no idle polling pulse. Its counter remained zero; scope capture requires an external PA8 button press. The timed body starts after debounce and includes fault-frame submission. Wiring unchanged. Serial evidence: `logs/lab3-can/20261019-050709-n3-test-btn-probe.log`.


## Built-in B1 measurement firmware

The user replaced the external PA8 test-button plan with the Nucleo built-in
blue B1 button. The baseline overlay now maps TEST_BTN to PC13 active-low,
matching the installed board's sw0 definition. The CAN/probe wiring, SPI clock
request, watchdog configuration and measurement task bodies remain unchanged.

Both N2 and N3 were rebuilt and flashed using freshly discovered serial-matched
ST-LINK drives. Correct online banners and timing records passed. N3 accepted
`timing probe test_btn` and is selected for the physical B1-press capture. Physical
press verification is pending. No external PA8 button is needed. The TEST_BTN
pulse starts after debounce and covers processing a press, including fault-frame
submission on both buses; it does not pulse continuously while unpressed.

Current deployed archive: `logs/lab3-can/20261019-051047-b1-measurement-build/`.
The earlier 043636 archive precedes this button mapping change. Checksums:
- N2 066BFF505487525067171333: `7d3be6a78ce5ef22e516c3efb69b790cba11e7bd67e4c3d2466325411e4b213b`; boot log `logs/lab3-can/20261019-051047-b1-flash-n2-COM4.log`.
- N3 066BFF485270535067124020: `5861456bfef9aff21fdc2fdbaca95ff41f1c2e2867e32219758bb2993c19bfa8`; boot log `logs/lab3-can/20261019-051047-b1-flash-n3-COM6.log`.

`tests/check_lab3_button.py` checks the generated devicetree against the board's
B1 GPIO controller, pin and active polarity. It failed against the original PA8
mapping and passed both rebuilt images. Use trusted local `zephyr/edt.pickle`
artifacts and Zephyr's python-devicetree module on PYTHONPATH.

Persistent deployment summary: `logs/lab3-can/b1-deployment-latest.json`.
Full serial logs also retain any crash reports; matching ELFs are in the archive.
No crash report was observed in these startup captures.


### N3 built-in B1 TEST_BTN scope result

IMG_0844 shows PC8 TEST_BTN positive pulse width after ten requested B1 presses:
current/minimum 850 us, mean 911.00 us, maximum 1.240 ms, standard deviation
133.81 us, count 10. Horizontal 500 us/div, CH1 1 V/div, trigger 1.50 V rising.
The photo and press sequence confirm B1 now activates the measured worker.
Evidence: `logs/lab3-can/test-btn-stats-IMG_0844.JPG`.

### Follow-up after remaining measurements

At the user's request, continue remaining captures first, then revisit these
handout comparisons and remind the user before closing the measurement session:
- HB_TX: selected 790 us versus 120 us placeholder. Two MCP2515 submissions use
  30 SPI bytes total, about 366 us of clocks at 656.25 kHz before overhead.
- PID-demo: 11 us versus 200 us placeholder. Inspection of deployed ELF shows the
  dummy calculation optimized away; real control computation remains missing.
- CAN_RX: 24 us measures application dispatch only; the handout's 80 us includes
  ISR and driver work, which still needs separate measurement.

Handout references: task template pages 7-8; measurement boundaries section 3.1,
page 11. These review items do not replace the recorded scope results.

Next capture: N3 selected `drive` on PC8. A bounded 75-second Pi SocketCAN stream submitted CTRL on both buses every 20 ms, zero steering/throttle and brake=100. No N1 heartbeat or fault-clear frames were sent; existing error/manual-error state was retained. This exercises the demo braking/error branch. The sender exited and its sockets closed. Serial: `logs/lab3-can/20261019-051704-n3-drive-capture.log`; stimulus PID/count/exit evidence: `logs/lab3-can/20261019-051704-drive-stimulus.log`. Scope result pending.


### N3 DRIVE-demo scope result

The user reported a consistent 12 us pulse during the second CTRL stream;
selected measured maximum 12 us. No photograph or scope sample count was
supplied. Input was zero steering/throttle, brake=100, every 20 ms on both
buses; no N1 heartbeat or fault clear was sent. This is the current demo
braking/error path, not a complete motor-control implementation.

The second stream started after explicit readiness confirmation with a 120 s
limit. The user supplied the result while the tool call was interrupted. The
agent then verified remote PID 2049 was still the stimulus Python process,
sent SIGINT and verified it exited. No CTRL stimulus is left running.
Evidence: `logs/lab3-can/20261019-052059-drive-retry-stimulus.log`,
`logs/lab3-can/20261019-052059-n3-drive-retry.log`, and
`logs/lab3-can/drive-retry-cleanup.log`.

Next measurement is N2 FORCE_TX. It requires moving CH1 to N2 PC8/CN10-2,
CH2 to N2 CAN A CS PB6/D10, and selecting `force_tx` after power restoration.
The probe move is requested, not yet confirmed. N3's last selection remains
`drive`. Existing automatic heartbeat/FORCE firmware traffic continues.


## PID and CAN measurement revision, October 19

The user changed the measurement order: stay on N3, repair the earlier workload
and boundary gaps, then remeasure before moving to N2. They chose reuse of the
Lab 2 PID calculation with synthetic feedback. The 1 MHz SPI request, B1/PC13,
PC8/CH1 and PB6/CH2 wiring, and non-actuating behavior remain unchanged.

### PID workload

N3 now links the unchanged `bringup/motor_test/src/velocity_control.c` directly,
not a copied approximation. No motor driver, encoder driver or PWM output is
linked. The 10 ms worker supplies one synthetic 20 ms encoder sample per
activation, so the Lab 2 core's 20 ms minimum interval does not skip alternate
computations. This is independent synthetic time, not a live 10 ms control loop.
Three 100-sample phases use targets 150/300/23 RPM and encoder increments
44/88/132 per 20 ms, equivalent to 100/200/300 RPM. The third phase starts a
fresh controller to exercise the lower clamp. The 300-sample cycle repeats with
bounded counts; outputs remain observable through `PID_WORKLOAD` telemetry.
The pulse includes fixture preparation, real PID calculation, result conversion
and marker work; publishing/printing telemetry happens afterward. N3 enables
FPU/FPU_SHARING like Lab 2. STEER and DRIVE remain GPIO stand-ins.

Host tests verify independently worked initial outputs 66.35 and 66.70 percent,
changing outputs, both duty clamps and repeated fixture cycles. Target startup
records show duties 66350, 40000, 100000 and 86649 milli-percent with status=0.
Disassembly confirms pid_thread calls lab3_pid_measurement_step, which calls
velocity_update and velocity_retarget; calculation survives optimization.

### Heartbeat and receive boundaries

- Existing HB_TX elapsed pulses are retained. `OBS_THREAD name=hb_tx` separately
  reports per-activation thread-accounted execution, using 64-bit runtime deltas.
  It excludes switched-out time but can include IRQ time charged to the thread;
  it also includes measurement-call overhead around the GPIO body. It is not
  the earlier elapsed counter under another name. Runtime stats are enabled on
  both nodes, adding scheduler instrumentation overhead.
- `timing probe rx_dispatch_a` and `rx_dispatch_b` restrict the GPIO marker to
  one bus without changing processing. Aggregate `rx_dispatch` still works.
- `rx_callback_to_end_a/b` measure each frame's own callback-entry timestamp to
  dispatch completion, including post-body bookkeeping. These exclude earlier
  GPIO ISR and SPI/driver receive work; they are not full CAN_RX time.
- `timing tx off|on` gates new application CAN submissions. Already submitted
  frames can finish; callers retain their periodic tasks and state processing.
  Default is on. Both boards acknowledged off, a three-second Pi capture was
  quiet, then both acknowledged on. Normal automatic traffic is restored.
- For the later full receive elapsed measurement, pause TX on BOTH boards,
  verify the bus is quiet, then inject isolated valid frames on Pi can1, which
  reaches N3 CAN A. With CH2 moved to PA10 INT and CH1 selected rx_dispatch_a,
  measure INT falling to the matching dispatch pulse's end. This physical
  measurement is pending. Avoid pairing unrelated TX/error interrupts or a
  batch of multiple received frames with a single dispatch.

### Deployment and pending capture

Archive: `logs/lab3-can/20261019-053026-pid-rx-measurement-build/`. It includes both images/ELFs, generated
configurations/devicetrees, app sources, the externally linked Lab 2 source and
SHA-256 manifest. Both images passed startup/timing validation; the B1 generated
configuration test still passes. N3 accepted rx_dispatch_a and was finally
selected to **pid**. Normal TX is on; no Pi stimulus or test server is running.
The physical probes have NOT moved. The next step is the revised PID scope
capture on N3, followed by revised heartbeat and isolated receive measurements.

Earlier scope results remain associated with their earlier firmware. The 11 us
PID-demo result belongs to the removed empty workload, not the new calculation.
Startup software counters reported PID max 16 us, heartbeat elapsed max 817 us
at the sampled records and heartbeat thread-accounted max up to 646 us; these
are serial startup observations, not new scope results.

Evidence:
- `logs/lab3-can/measurement-revision-deployment.json`
- `logs/lab3-can/measurement-revision-host-tests.log` (five tests passed)
- `logs/lab3-can/revised-n3-disassembly.log`
- timestamped `*-revision-build-*`, `*-revision-flash-*`, `*-tx-gate-*` and
  `*-tx-off-quiet.log` under `logs/lab3-can/`.
Serial logs retain crash reports; matching ELFs are in this archive. No crash
report was observed during the successful startup captures.

N2 binary SHA-256: `e9f3c74364add5679d2872d1ddddd32f91428b08bb45505d5818d77ad4887f1e`.

N3 binary SHA-256: `daa66c9893b68ede9ceec379da4bcee0ea33f58a0e647ee17c133178cf6b28b5`.


### Revised N3 Lab 2 PID calculation scope result

On the 053026 PID/RX measurement firmware, the user reported maximum **18.8 us**
and mean **14.5 us** for PC8 selected to `pid`. No minimum, sample count, photo
or independently verified collection duration was supplied. This replaces the
old 11 us empty-demo result for the selected PID calculation workload; the old
result remains historical evidence of its original firmware.

The real unchanged Lab 2 velocity calculation is linked and observable, with
FPU/FPU_SHARING enabled. This workload excludes physical encoder acquisition and
motor/PWM output. Its 18.8 us maximum corresponds to about 1579 cycles at 84 MHz.
The handout's 200 us placeholder is not a minimum workload duration.

Next remeasurement selected: N3 `hb_tx`, accepted on COM6. CH1 remains PC8; CH2 remains PB6 CS; automatic TX remains on. Serial heartbeat elapsed/runtime records: `logs/lab3-can/20261019-053553-revised-hb-tx-probe.log`. Revised heartbeat scope result pending.


### Revised N3 heartbeat TX scope result

IMG_0845 confirms the pulse is visible after the no-signal report and reselection.
On the 053026 PID/RX measurement revision, PC8 selected `hb_tx` shows:

| Statistic | Positive pulse width |
|---|---:|
| Current | 815 us |
| Minimum | 810 us |
| Mean | 814.69 us |
| Maximum | 815 us |
| Standard deviation | 1.2026 us |
| Count | 585 |

Scope horizontal 500 us/div; both channels 2 V/div; CH1 rising trigger 1.50 V.
The photo shows acquisition running. Evidence:
`logs/lab3-can/revised-hb-tx-stats-IMG_0845.JPG`.
This is the revised-build heartbeat scope result. Keep the earlier 790 us result
under its earlier firmware, rather than mixing capture windows. The latest
serial check separately reported heartbeat thread-accounted maximum 675 us;
see `logs/lab3-can/20261019-053906-hb-no-signal.log`.

Next is isolated full CAN A receive elapsed timing on N3. The requested physical
change is CH2 from PB6/D10 CS to PA10/D2 INT, with CH1 still PC8/CN10-2. Power-off
move and subsequent external-power-before-USB restoration are not yet confirmed.
After readiness, select `rx_dispatch_a`, pause application TX on both boards,
verify bus quiet, and inject isolated valid frames only on Pi can1. Do not start
the stimulus until the user is ready. Measure CH2 falling to the matching CH1
falling edge, not just CH1 pulse width. No traffic was paused for this transition
yet; normal firmware TX continues until the coordinated receive test.

Isolated N3 CAN A receive run 20261019-054335: user confirmed CH2 PA10 wiring ready; both nodes acknowledged TX off, then a three-second Pi capture was quiet. N3 selected rx_dispatch_a. Pi can1 submitted valid CTRL frames every 100 ms for 120 s, steering/throttle zero and brake=100. No N1 heartbeat or fault clear was injected. Sender exited; both boards remain application-TX paused to preserve the capture until the scope result is recorded. Scope interval is CH2 falling to matching CH1 falling. Evidence: `logs/lab3-can/20261019-054335-isolated-rx-stimulus.log`, `logs/lab3-can/20261019-054335-isolated-rx-COM6.log`, and `logs/lab3-can/20261019-054335-rx-quiet.log`.


### N3 isolated CAN A INT-to-dispatch-completion scope result

IMG_0848 shows the requested bottom-row delay, CH2 falling to CH1 falling:

| Statistic | Delay |
|---|---:|
| Current | 402 us |
| Minimum | 402 us |
| Mean | 402.08 us |
| Maximum | 404 us |
| Standard deviation | 383.49 ns |
| Count | 158 |

CH1 is PC8 selected rx_dispatch_a; CH2 is PA10/D2 CAN A INT. Horizontal is
200 us/div; both channels 1 V/div; trigger is CH2 falling at 1.50 V. The photo
shows acquisition running. Only the bottom-row falling-to-falling delay is used
for this result; the separate negative rising-edge delay and uncounted/clipped
positive-width measurement are not substituted for it.

This is isolated INT assertion to completion of the matching application's
receive dispatch, with both MCU application transmitters paused and valid CTRL
frames injected only on Pi can1 every 100 ms, steering/throttle zero, brake=100.
It includes the elapsed ISR/driver/SPI/queue/dispatch path, not CAN reception
before INT assertion or driver cleanup after dispatch. It is kept separate from
the earlier 24 us dispatch-only result and the handout's task execution budget.
Evidence: `logs/lab3-can/rx-int-to-dispatch-stats-IMG_0848.JPG`.

At the user's explicit request the continuous stream was left running until
this result arrived. It was then stopped because the next test requires a
power-off probe move to N2. PID 2161 exited after 858 frames; its sockets closed.
Stop evidence: `logs/lab3-can/continuous-rx/stop-2161.log` and
`logs/lab3-can/continuous-rx/stopped-state-2161.json`. The remote stream log is
retained at the path in that state file; the stopped temporary stream script
was removed. No receive-stimulus process remains running.

The requested N3 remeasurements are now: real Lab 2 PID synthetic workload
max 18.8 us / mean 14.5 us; heartbeat TX max 815 us / mean 814.69 us; isolated
INT-to-dispatch completion max 404 us / mean 402.08 us. The old PID stub and
partial receive measurement are no longer confused with these workloads.
Next is N2 FORCE_TX, requiring the physical probe move; not yet performed.

Both boards acknowledged `timing tx on` after the receive capture. Normal automatic traffic is restored. Evidence: `logs/lab3-can/20261019-055017-rx-finish-restore-COM4.log` and `logs/lab3-can/20261019-055017-rx-finish-restore-COM6.log`.


### Logical node roles swapped without moving probes

The user chose to swap firmware roles rather than move probes. The same archived
053026 binaries were hash-checked and flashed to the opposite ST-LINK identities:

| Logical node | ST-LINK | Port at deployment | Drive |
|---|---|---|---|
| N2 | 066BFF485270535067124020 | COM6 | E: |
| N3 | 066BFF505487525067171333 | COM4 | D: |

Both correct online banners and timing records passed. The probed physical board
is now N2; it accepted `timing probe force_tx`. CH1 remains PC8/CN10-2 and CH2
remains PA10/D2 INT, not CS. Physical CAN wiring, 1 MHz SPI request, B1 mapping
and non-actuating behavior are unchanged. Normal application TX is on.

Because logical identities moved, the current bus labels are:

| Pi interface | New N2 label | New N3 label |
|---|---|---|
| can0 / CE1 | B | A |
| can1 / CE0 | A | B |

Earlier measurements remain attached to their original logical role, physical
board and firmware; do not relabel historical captures retroactively. Current
deployment metadata: `logs/lab3-can/role-swap-latest.json`; raw serial logs use
prefix `logs/lab3-can/20261019-055235-role-swap-`. The selected FORCE_TX scope result is
pending. No external stimulus was started.


### N2 FORCE_TX scope result after logical role swap

Probed board ending 124020/COM6 now runs N2. CH1 PC8 is selected force_tx;
CH2 remains PA10 INT. IMG_0850 shows positive pulse-width statistics:
current/minimum 805 us, mean 924.46 us, maximum 1.050 ms, standard deviation
119.79 us, count 202. Horizontal 500 us/div; channels 2 V/div; CH1 rising-edge
trigger at 1.50 V. Acquisition is running in the photo.
Evidence: `logs/lab3-can/force-tx-stats-IMG_0850.JPG`.

The user reports alternating between two relatively stable widths. The 50 ms
FORCE and 20 ms heartbeat periods have a repeating 100 ms relative phase;
competing heartbeat/driver work is a plausible explanation, not a traced causal
attribution. The screenshot's extrema and distribution support two clusters but
do not by themselves show their temporal order.

Next is STEER. Its current N2 body only toggles a GPIO marker; no steering
calculation or servo PWM is implemented. User decision requested whether to
reuse the Lab 2 steering calculation without servo output before measuring it,
or retain the explicitly labeled marker-only measurement. FORCE_TX remains
selected and normal firmware TX remains on; no external stimulus is running.


## Lab 2 steering calculation measurement revision

The user chose to replace N2's GPIO-only STEER body with the existing Lab 2
steering calculation before measuring it. The application links unchanged
`stm32_zephyr/src/servo_core.c`; its adapter calls `servo_map` using the tracked
`config/servo_calibration.json` endpoints 1200/1600/2000 us. CMake generates the
same calibration header template as Lab 2 and rejects invalid endpoints. This
measures calibrated mapping, not servo PWM output or the complete autonomous
steering policy. The pulse ends before publishing output telemetry. No servo
hardware driver or PWM application code is linked into this workload.

Host tests check all five selected positions, exact endpoints/midpoints and
monotonicity across the complete int16 command range. All six measurement tests
passed. Both rebuilt images passed B1 configuration checks and boot validation,
retaining the swapped roles: N2 ending124020/COM6, N3 ending171333/COM4.
No physical wiring moved: CH1 PC8 and CH2 PA10 INT on the now-N2 board.

Current build archive: `logs/lab3-can/20261019-060412-steering-measurement-build/`. It includes both binaries/ELFs,
configs/devicetrees, generated N2 calibration header, app sources and externally
linked Lab 2 PID/servo sources and calibration, with SHA-256 manifest. Earlier
measurement results retain their original firmware archive labels.

N2 binary SHA-256 `fb807214eb41b3c5546cafa43127b0bedfbef4a34dd782d4a04c319b537724a6`; boot evidence `logs/lab3-can/20261019-060412-steering-flash-n2-COM6.log`.

N3 binary SHA-256 `853b7dfe53f0f264bc2f8ab1e91ed97d14dbc7edd5dd44e3dd9959b7c3d374c5`; boot evidence `logs/lab3-can/20261019-060412-steering-flash-n3-COM4.log`.


N2 accepted `timing probe steer`. Both boards have normal application TX on.
A user-authorized continuous Pi stimulus is running on both CAN interfaces,
period 20 ms, steering positions 0/-32768/-16384/16384/32767 held for 25 frames
each, throttle=0 and brake=100. No N1 heartbeat or fault-clear is injected.
The mapping workload consumes accepted commands despite the surrounding demo's
error state; it only reports results and never applies them to a servo.

Target evidence `logs/lab3-can/20261019-060538-steering-live-verification.log`
shows STEER sample count increasing 899 to 1160, pulse values 1600 and 1200 us,
minimum 1200 and maximum 2000 us, hardware_output=0, and no TX rejects/failures.
Software timing maximum in that check was 7 us; scope result is pending.
`logs/lab3-can/revised-steering-disassembly.log` confirms control_thread calls
lab3_steering_pulse, which calls the original servo_map; work survives optimization.

Continuous sender PID 2227 is intentionally left running, per the
user's instruction to keep measurement traffic running unless stopping is
necessary. Ownership/start/stop tools and state are in
`logs/lab3-can/continuous-steer/`. Remote persistent stdout/crash-trace log:
`/home/labuser/.local/state/team4-lab3/steering-e456788e41304c8987cc44cba780c834/stream.log`. Stop only for a necessary test transition or user request;
do not end this capture after a fixed time. The older isolated-RX sender remains
stopped. Next: obtain the STEER scope maximum/mean/count with CH1 positive width.


### N2 Lab 2 steering-map scope result

On the 060412 steering revision, IMG_0851 shows CH1 PC8 selected `steer`:

| Statistic | Positive pulse width |
|---|---:|
| Current | 9.6 us |
| Minimum | 9.6 us |
| Mean | 9.6768 us |
| Maximum | 9.8 us |
| Standard deviation | 97.374 ns |
| Count | 518 |

Horizontal 20 us/div, both channels 2 V/div, CH1 rising trigger 1.50 V;
acquisition is running in the photo. CH2 remains PA10 INT. Evidence:
`logs/lab3-can/steering-stats-IMG_0851.JPG`.
The command stream is the continuous five-position, dual-bus, 20 ms synthetic
CTRL workload documented above, throttle=0/brake=100. The pulse measures the
real calibrated Lab 2 mapping plus its GPIO/timing instrumentation, without
physical servo output or the full autonomous steering policy.

The planned individual MCU task-body captures are recorded. Pending separate
work includes Pi UDP-to-CAN idle/stress latency, broader fault/relay timing and
any additional per-node/bus coverage required for analysis. No task graph was
created. The continuous steering sender PID 2227 is intentionally still running
while the next measurement path is inspected; stop it before another process
publishes the same CTRL stream.


## Pi UDP-to-CAN idle/stress measurements

The user selected synthetic wheel-format UDP rather than the physical wheel
proxy. A laptop generator sent valid 276-byte datagrams to the real live-mode
bridge on Pi UDP 8000, nominally every 20 ms, for 65 seconds in each trial.
Steering cycled through five positions; throttle was zero and brake 100 percent.
GPIO tracing was disabled. No firmware or CAN wiring changed for these trials.

The bridge first required two python-can listener fixes: Receiver now subclasses
can.Listener and each Notifier receives a list containing that listener. A real
Notifier/virtual-bus reception test and a real-main startup test reproduced the
two errors before the fixes. All 11 Pi receiver/protocol/wheel tests then passed.
The measurement source snapshot and hashes are retained with the results.

One preliminary idle attempt was excluded because the test supervisor delivered
duplicate SIGINTs while stopping its timeout-wrapped bridge. Its evidence is in
attempt-idle-interrupted-shutdown/. The supervisor was corrected to signal only
the wrapper, and both reported trials were rerun with verified clean shutdown.

### Results, microseconds

The full software interval is paired PER COMMAND: UDP receive-to-pre-send plus
that command's marker-to-send-start gap plus its two-send-call duration. Maxima
from different commands are never added. It ends when both SocketCAN calls
return, not at physical CAN transmission or at an MCU output.

| Condition | Fresh commands | UDP receive to pre-send max / p99 | Two CAN calls max / p99 | UDP receive to both returns max / p99 |
|---|---:|---:|---:|---:|
| idle | 3244 | 619.137 / 334.253 | 1495.955 / 987.260 | 1774.950 / 1240.662 |
| stress | 3243 | 4385.198 / 157.163 | 5858.301 / 4070.518 | 5963.539 / 4235.923 |

Both trials sent and received 3250 datagrams, with no skipped laptop send slots,
UDP rejects, old-sequence rejections or CAN-send errors. The bridge intentionally
keeps the newest datagram when several are drained in one loop: 6 idle and 7
stress datagrams had no separate command record. Reported spans were 64.986 s
idle and 64.979 s stressed. These timestamps start after userspace recvfrom,
so they exclude packet travel and time waiting in the UDP receive queue.

Stress was four separate, bounded integer-arithmetic workers, one per Pi core
by process count, without CPU pinning, priority changes or governor changes.
Aggregate CPU busy was 5.27 percent idle and 99.85 percent stressed, measured over
the supervisor windows. The governor remained ondemand. Sampled frequency was
1.8 GHz before/after stress; idle ended at 700 MHz. Temperature was 44.79 C in
idle snapshots and 53.069 to 75.471 C under stress. Throttling flags were 0x0 in
all snapshots. Do not infer a precise cause for tail latency from these two
frequency snapshots alone.

All trial bridge/load processes exited and Pi UDP 8000 was verified free. The
previous steering-only sender was stopped before trials to prevent duplicate
CTRL publishers. Afterward, the continuous non-actuating steering sender was
restored per the user's keep-running instruction; it is the only test stimulus
left running. Both Nucleos retain normal automatic firmware TX, and PC8 on
N2/COM6 remains selected to steer. No probe changes were made.

Persistent local evidence: `logs/lab3-can/20261019-061302-pi-latency/`, including idle.csv, stress.csv, sender logs, state snapshots, summary.json, source hashes, startup/crash logs and final-environment-and-cleanup.json. Matching remote trial artifacts are at `/home/labuser/.local/state/team4-lab3/20261019-061302-pi-latency`.

Current continuous steering PID: 2643; ownership/start/stop files remain in `logs/lab3-can/continuous-steer/`. Remote persistent log/crash path: `/home/labuser/.local/state/team4-lab3/steering-beede81435b34cc586be293fcce91187/stream.log`.


## Stressed Pi latency investigation

User chose diagnosis before Pi GPIO scope verification. A separate instrumented
bridge copy recorded wall time, thread CPU time, voluntary/involuntary context
switches, CSV lock acquisition and writer duration. Slow events were buffered in
memory and saved after shutdown, not printed in the critical path. The tested
production bridge source was not changed for performance.

In the instrumented stressed trial, a main-thread CSV write took 5964.686 us
elapsed but only 34.351 us CPU, with zero voluntary and one involuntary context
switch. Lock acquisition was only 1.407 us. Other large delays occurred inside
select and socket-send wrappers, e.g. select 5846.411 us elapsed / 14.315 us CPU
with an involuntary switch. This establishes CPU descheduling during those
outliers; CSV lock contention or computation alone does not explain them.
Socket/GIL waits can also contribute to other events. Nested diagnostic timing
records overlap and are not added together. These are diagnostic, not substitute
unmodified-bridge benchmark values.

Independent CSV review of the original 65-second trials found 71 stressed send
groups over 2 ms, 68 dominated by the interval from the can0 marker to can1 marker.
Those intervals include synchronous CSV logging as well as Python message
construction and CAN sends. One 4620 us pause occurred before either send marker.
The previously named receive-to-both-send-returns aggregate is more precisely
**userspace receive to dual-CAN submission-group completion**, including the
synchronous log writes within send_both. Its numeric values are unchanged.

A controlled uninstrumented 20-second comparison retained FOUR CPU load workers
and changed only bridge affinity, pinning all bridge threads to CPU3 in the
second case:

| Configuration | Fresh commands | Group-completion max / p99, us | Commands above 2 ms |
|---|---:|---:|---:|
| unpinned | 993 | 6839.688 / 1998.666 | 9 |
| cpu3 | 997 | 4573.804 / 3631.840 | 26 |

Pinning did not solve the tail and was not adopted. Its process-specific affinity
ended with the test process; no global scheduler, governor or CAN settings changed.
All diagnostic/affinity bridge and CPU workers exited, and UDP8000 was verified
free. The continuous steering sender was restored as PID 2908.

Pi sudo requires authentication; RLIMIT_RTPRIO and RLIMIT_NICE are both zero.
A proposed next experiment is temporary lowest-priority SCHED_FIFO for the bridge,
requiring sudo approval, not a permanent system policy. User decision is pending.
Pi GPIO scope verification remains pending.

Evidence: `logs/lab3-can/20261019-062822-pi-latency-diagnosis/` for detailed stage events and
`logs/lab3-can/20261019-063104-pi-affinity-comparison/` for paired affinity trials and cleanup checks.
Permissions evidence: `logs/lab3-can/pi-scheduling-permissions.log`.
Continuous-stream ownership/log/crash paths remain in
`logs/lab3-can/continuous-steer/state.json`.


## Pi temporary real-time scheduling result

The user approved the real-time scheduling trial. Sudo authorization was supplied
through SSH stdin only; credentials were not stored in project files or test
logs. The actual bridge main thread and both CAN notifier threads were verified
SCHED_FIFO priority 1 before collecting data. This was a per-process experiment,
not installation of PREEMPT_RT or a persistent OS scheduling change.

The same four normal-priority CPU load workers remained active. The laptop sent
3250 valid synthetic UDP packets at nominal 20 ms intervals for 65 seconds.
All 3250 arrived, with no UDP rejects/old sequences or CAN-send errors. The
bridge's newest-input policy combined 104 queued updates, yielding 3146 measured
commands. First and last input sequence and a 64.977 s measured span were verified.

| Pi software interval | Maximum | p99 |
|---|---:|---:|
| UDP userspace receive to pre-send | 312.698 us | 123.146 us |
| UDP userspace receive to dual-CAN submission-group completion | 477.621 us | 401.066 us |

No measured submission-group sample exceeded 2 ms. For comparison, normal
scheduling under the original four-worker load gave max 5963.539 us / p99
4235.923 us for the same software group boundary. The group includes synchronous
CSV writes inside send_both and ends before physical CAN delivery. The increase
in coalesced updates is retained in the result, not hidden as packet loss or
counted as individual command executions.

At shutdown, another KeyboardInterrupt interrupted notifier cleanup AFTER the
complete collection window. The result was initially rejected by a broad
traceback check, then specifically validated: no exception before 'Stopping N1',
all sent datagrams present, valid complete CSV rows, no unmatched command timing
rows, and the final sent sequence represented. The post-run cleanup issue is
recorded rather than treating it as an in-window data failure. Timeout wrapper,
actual Python bridge and all load workers were verified gone; UDP8000 was free.

Evidence: `logs/lab3-can/20261019-063643-pi-realtime-trial/summary.json`, stress.csv, sender.csv,
stress-bridge.log, stress-state.json, process-exit-verification.json and matching
controller/bridge sources. No password is in the source snapshot. No real-time
process or persistent priority setting remains after this test. Future launches
must explicitly reapply the chosen scheduling policy; restarting plain Python
will revert to normal scheduling.

Per the user's keep-running instruction, the normal continuous steering stimulus
was restored as PID 3046; state/start/stop and remote stdout/crash-log
paths remain in `logs/lab3-can/continuous-steer/`. Both Nucleos retain normal TX,
N2/COM6 remains selected to steer, and physical probes are unchanged. Pi GPIO
scope verification is still pending; these results are software timestamps.

Pi GPIO scope transition 20261019-064143: stopped owned continuous steering sender PID3046, requested orderly Pi shutdown and verified SSH no longer reachable. No stimulus remains running. Requested probe move is CH1 to Pi BCM17/physical11 and CH2 to BCM27/physical13, grounds to Pi GND/physical6. Physical move and power restoration are pending. Nucleo roles/firmware unchanged. Shutdown/stop logs use `logs/lab3-can/20261019-064143-pi-*`.


### Pi GPIO scope setup active

The user confirmed the probe move after orderly Pi shutdown. CH1 is now Pi
BCM17/physical11 and CH2 BCM27/physical13, with Pi ground. On reboot both CAN
interfaces were down; controller identities were verified can0=spi0.1 and
can1=spi0.0, then both restored to 500 kbit/s. GPIO17/27/22/23 were unclaimed.

The old independent toggle markers could lose edge pairing when UDP updates
were combined, or when stale commands repeated. A regression test reproduced
that issue. The traced implementation now starts one GPIO17 edge at the first
UDP receive in a drained batch and makes GPIO27 match immediately before the
command group. Further receives in that batch and stale repeats add no extra
edge. Thus rising-to-rising and falling-to-falling pairs remain matched under
the controlled valid UDP workload. The new UDP_BATCH_TO_CMD_TX CSV event times
first received packet in batch to pre-send; existing UDP_TO_CMD_TX retains its
latest-packet boundary. Scope pairing is batch timing, with GPIO call overhead.
All 12 Pi receiver/protocol/wheel/marker tests passed before startup.

A traced bridge is running as remote PID 1587, all three threads verified
FIFO priority1. Laptop synthetic UDP sender PID 30956 runs continuously
at 20 ms, five steering positions, throttle0/brake100. GPIO requests were verified
owned by lab3-dual-can and the bridge reports fresh UDP. No CPU stress is active;
next capture is idle. The user wants streams kept running unless a transition
requires stopping. Ownership and cross-platform start.py/stop.py are in
`logs/lab3-can/pi-scope/`; remote CSV/stdout/crash paths and source hashes are
in state.json. Controller startup uses stdin-only sudo authentication and stores
no credential. Source STM32 firmware and node-role swap are unchanged.


### Pi idle GPIO scope result

IMG_0853 shows CH1 rising to CH2 rising, paired UDP-batch receive to pre-send:
current228 us, minimum196 us, mean230.20 us, maximum808 us, standard deviation
37.254 us, count1.159k. Horizontal200 us/div; channels2 V/div; CH1 rising trigger
1.50 V. Acquisition is running in the photograph. The bridge is FIFO1 with
GPIO tracing on and no CPU load workers; the synthetic laptop stream is20ms.
Photo: `logs/lab3-can/pi-idle-scope-IMG_0853.JPG`.

A separate last-65-second software companion window before enabling stress
contains 3240 UDP_BATCH_TO_CMD_TX records, span 64.976s,
maximum 530.320us and nearest-rank p99 254.606us.
It includes both edge polarities and is not the exact scope acquisition window.
Software timestamps exclude some GPIO syscall edge overhead. Raw CSV and summary
are `logs/lab3-can/pi-scope/idle-before-stress.csv` and idle-batch-companion.json.

Next capture is stressed GPIO delay. Keep the bridge and UDP sender running and
enable four normal-priority CPU workers, then reset scope statistics.

Stress load is now running as PIDs [1658, 1659, 1660, 1661]; bridge FIFO1 was reverified and load workers are SCHED_OTHER. Ownership/phase boundary is `logs/lab3-can/pi-scope/load-state.json`. Stress scope result pending.


### Stressed Pi coarse-timebase capture, repeat requested

IMG_0854 was taken at 10 ms/div, rather than the requested 200 us/div. Its
CH1-rising to CH2-rising display reads current/minimum100 us, mean128.57 us,
maximum200 us, standard deviation45.305 us, count175. The displayed 100 us
steps are too coarse for comparison with the prior microsecond-resolution
capture. Preserve these as displayed preliminary readings, not the selected
stressed result. Requested repeat: 200 us/div, reset statistics, same edge pair
and 60-second collection. Bridge, sender and all four load workers remain
running unchanged for the repeat. Photo: `logs/lab3-can/pi-stress-coarse-IMG_0854.JPG`.


### Pi stressed GPIO scope result

IMG_0855 at the restored200 us/div timebase shows CH1-rising to CH2-rising delay:
current120 us, minimum106 us, mean118.91 us, maximum246 us, standard deviation
9.8353 us, count399. Channels2 V/div, CH1 rising trigger1.50 V; acquisition is
running. This is the selected stressed scope result, replacing the coarse
IMG_0854 reading. Photo: `logs/lab3-can/pi-stress-scope-IMG_0855.JPG`.

The traced FIFO1 bridge and20ms synthetic UDP sender remained unchanged. Four
normal-priority CPU workers ran throughout this capture/repeat; aggregate CPU
busy over the recorded load interval was 99.99 percent. Scope collection
duration was requested as60s but is not independently established by the photo.

A separate last65s software companion window while load was active has
3246 batch timing records over 64.994s, maximum
362.347us and nearest-rank p99 212.756us. It includes
both edge polarities and is not the exact scope acquisition window; GPIO-edge
overhead is also different. Raw CSV and summary: pi-scope/stress-before-stop.csv
and stress-batch-companion.json under logs/lab3-can. Do not label this p99 as a
percentile calculated from the scope's summary statistics.

After recording the result, only CPU workers [1658, 1659, 1660, 1661] were stopped and
verified exited. Load cleanup evidence: `logs/lab3-can/pi-scope/load-stop.log`,
load-stopped-state.json and stress-cpu-utilization.json. The FIFO1 bridge
PID1587 and laptop sender PID30956 remain running per the
user's keep-running instruction; no stress load remains.
