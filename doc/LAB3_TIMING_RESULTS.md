# Lab 3 measured timing results

Selected bench results from October 19, 2026. This is a measurement ledger, not a task graph or a schedulability analysis. Detailed evidence, workload changes and deployment history are in [LAB3_CAN_BRINGUP.md](LAB3_CAN_BRINGUP.md).

## STM32 scope measurements

Times are microseconds. Node names are the logical roles **at measurement time**; the firmware roles were subsequently swapped without moving the probes. All task-body values include the work between the selected PC8 edges.

| Logical node | Measured operation | Maximum | Mean | Count | Build | Evidence |
|---|---|---:|---:|---:|---|---|
| N3 | Heartbeat TX, dual-bus submission | **815** | 814.69 | 585 | 053026 | [IMG_0845](lab3-scope/revised-hb-tx-stats-IMG_0845.jpg) |
| N3 | Heartbeat monitor | **19** | 19 | Not supplied | 043636 | User report |
| N3 | Application receive dispatch only | **24** | 23.503 | 965 | 043636 | [IMG_0843](lab3-scope/rx-dispatch-stats-IMG_0843.jpg) |
| N3 | Blinker body | **15** | 15 | Not supplied | 043636 | User report |
| N3 | Real Lab 2 PID calculation on synthetic samples | **18.8** | 14.5 | Not supplied | 053026 | User report |
| N3 | Built-in B1 accepted-press processing | **1240** | 911.00 | 10 | 051047 | [IMG_0844](lab3-scope/test-btn-stats-IMG_0844.jpg) |
| N3 | DRIVE GPIO demo, braking/error branch | **12** | 12, set equal to max by user decision; no mean captured | Not supplied | 051047 | User report |
| N3 | Isolated CAN A INT assertion to dispatch completion | **404** | 402.08 | 158 | 053026 | [IMG_0848](lab3-scope/rx-int-to-dispatch-stats-IMG_0848.jpg) |
| N2 | FORCE_TX, dual-bus counter submission | **1050** | 924.46 | 202 | 053026 | [IMG_0850](lab3-scope/force-tx-stats-IMG_0850.jpg) |
| N2 | Real Lab 2 calibrated steering mapping | **9.8** | 9.6768 | 518 | 060412 | [IMG_0851](lab3-scope/steering-stats-IMG_0851.jpg) |

### October 21 additions

The same 060412 images were used. Scope CH1 was connected to the selected PC8 pulse and measured with +Width statistics. The FIFO-1 bridge sent synthetic UDP-driven CTRL, N1 heartbeat and left-blink frames. Both nodes ran in the same latched ERROR state as the October 19 captures. N3 CAN B was reset after a boot-time latch; see the bring-up record.

| Logical node | Measured operation | Maximum | Mean | Min | Count | Evidence |
|---|---|---:|---:|---:|---:|---|
| N2 | HB_TX, dual-bus heartbeat submission | **826** | 821.05 | 814 | 778 | [IMG_0858](lab3-scope/n2-hb-tx-IMG_0858.jpg) |
| N2 | HB_MON | **19** | 18.307 | 18 | 605 | [IMG_0859](lab3-scope/n2-hb-mon-IMG_0859.jpg) |
| N2 | BLINK_F, blink frame processing | **57** | 16.086 | 14 | 35 | [IMG_0860](lab3-scope/n2-blink-IMG_0860.jpg) |
| N2 | TEST_BTN, accepted B1 processing after debounce | **896** | 891.50 | 888 | 20 | [IMG_0861](lab3-scope/n2-test-btn-IMG_0861.jpg) |
| N2 | CAN_RX_A, isolated INT falling to dispatch completion (CH2 PA10 → CH1 PC8 falling) | **407** | 404.38 | 404 | 21 | [IMG_0862](lab3-scope/n2-rx-a-int-to-dispatch-IMG_0862.jpg) |
| N2 | CAN_RX_B, isolated INT falling to dispatch completion (CH2 PB5 → CH1 PC8 falling) | **406** | 404.86 | 404 | 22 | [IMG_0863](lab3-scope/n2-rx-b-int-to-dispatch-IMG_0863.jpg) |
| N1 (Pi) | UDP_RX rising → CMD_TX rising, post-write boundary, idle, FIFO 1 (scope); companion CSV last 180 s: max 1543.603, p99 **1060.389**, 8990 updates | **1460** | 558.81 | 480 | 4220 | [IMG_0864](lab3-scope/pi-idle-postwrite-IMG_0864.jpg) |
| N1 (Pi) | UDP_RX rising → CMD_TX rising, post-write boundary, four CPU workers, FIFO 1 (scope); companion CSV 212.7 s under load: max 1539.307, p99 **510.450**, 10508 updates | **910** | 279.95 | 250 | 2186 | [IMG_0865](lab3-scope/pi-stress-postwrite-IMG_0865.jpg) |
<!-- oct21-rows -->

**Pi stage for the report (handout boundary: UDP_RX → CMD_TX after both CAN writes):** idle scope max **1.46 ms**, CSV p99 **1.060 ms**; stressed scope max **0.91 ms**, CSV p99 **0.510 ms**. The largest CSV value is about 1.54 ms in both conditions. The CPU governor is `ondemand` (600 MHz–1.8 GHz). Under the four-worker load, CPU0 stayed at 1.8 GHz. A few seconds after the load stopped, it read 800 MHz. That frequency difference is the likely reason the stressed latency is lower; it was not isolated by a fixed-frequency test. Conservative chain input: about 1.54 ms, the largest value across both conditions, or 1.46 ms if only the scope values are used. Evidence: `logs/lab3-can/20261021-remaining/pi-*-postwrite*`.

N3 CAN_RX_B was not captured separately. The user approved reusing same-task STM32 values across boards, so the table uses the N2 CAN_RX_B result. Reuse is not allowed for N1/Pi rows. After these captures, the two boards' firmware roles were swapped via pyOCD: 124020 became N3 and 171333 became N2.

#### N1 software task bodies, October 21

These values come from instrumented `cockpit_bridge.py` CSV timestamps (`time.monotonic_ns`), not a scope. The run used FIFO 1, GPIO markers and synthetic UDP at 20 ms with the left-turn button held. It lasted about 836 s, and both MCUs were transmitting. Each body includes its synchronous CSV log writes. This run used the bridge revision before the CMD_TX fix; its `CTRL_SEND_GROUP` included the per-frame logs. The corrected bridge times only the two write calls. Evidence: `logs/lab3-can/20261021-remaining/n1-bridge-timing.csv` and `n1-task-summary.json`.

| N1 task | Measured body | Maximum | Mean | p99 | Count |
|---|---|---:|---:|---:|---:|
| UDP_RX | accepted datagram: recvfrom, marker, log, decode and freshness | **1726.377** | 168.564 | 404.364 | 41800 |
| CTRL_TX | dual SocketCAN CTRL group (`CTRL_SEND_GROUP`) | **2227.904** | 380.483 | 1021.392 | 41552 |
| BLINK_TX | blink decision and dual-bus group | **183979.228** (next 1558.119) | 554.150 | 987.001 | 1674 |
| HB_TX | dual-bus N1 heartbeat group | **2465.326** | 436.318 | 966.152 | 40860 |
| HB_MON | peer-health evaluation | **99.961** | 40.370 | 57.573 | 40860 |
| FORCE_RX | notifier callback for 0x300 before its log write | **148.349** | 64.928 | 91.184 | 33516 |
| HB receive | notifier callback for 0x101/0x102 | **178.793** | 64.5 | 91.5 | 167582 |

The corrected bridge (post-write CMD_TX, logs excluded) also measured CTRL_TX as the two write calls only, over 43,552 idle FIFO-1 updates: max **2628.730**, mean 282.3, p99 804.097 (`pi-idle-postwrite.csv`). Use this CTRL_TX value with the corrected boundary.

The 184 ms BLINK_TX sample was a whole-process stall. Its CAN frames were submitted on time, but no thread logged anything for 184 ms. That pattern indicates a buffered CSV write blocked on SD storage. The stall is retained because it is a real elapsed time for this logging design, but it is not CAN submission work.

### SPI 5.25 MHz re-measurement (October 21, build `20261021-spi10m-build`)

The user delegated the SPI choice. Both overlays now request `spi-max-frequency = <10000000>`, the MCP2515 maximum; SPI1 runs at 84/16 = 5.25 MHz. No other source changed except the boot log, which now prints the devicetree value. Images were flashed with pyOCD, with N3 on 124020 (probed) and N2 on 171333. All four links received with 0 rejects after boot. The FIFO-1 bridge and sender were running. These rows supersede the 656.25 kHz rows for the same tasks.

| Node | Measured operation | Maximum | Mean | Min | Count | Evidence |
|---|---|---:|---:|---:|---:|---|
| N3 | HB_TX, dual-bus heartbeat submission, 1 ms/div. Serial thread CPU-time maximum is 348 us; the remaining tail is blocking or preemption | **1270** | 306.31 | 260 | 545 | [IMG_0867](lab3-scope/spi10m-n3-hb-tx-IMG_0867.jpg) |
| N3 | TEST_BTN, accepted B1 processing after debounce, including FAULT submission on both buses | **850** | 384.78 | 340 | 23 | [IMG_0868](lab3-scope/spi10m-n3-test-btn-IMG_0868.jpg) |
| N3 | SPI1 SCK period on D13/PA5, verifying 84 MHz/16 | **192 ns** | 190.79 ns (5.24 MHz) | 188 ns | 1892 | [IMG_0869](lab3-scope/spi10m-sck-period-IMG_0869.jpg) |
| N3 | CAN_RX_A, isolated INT falling to dispatch completion (CH2 PA10 → CH1 PC8 falling) | **256** | 234.61 | 233 | 161 | [IMG_0871](lab3-scope/spi10m-n3-rx-a-IMG_0871.jpg) |
| N3 | CAN_RX_B, isolated INT falling to dispatch completion (CH2 PB5 → CH1 PC8 falling) | **287** | 233.73 | 233 | 1126 | [IMG_0872](lab3-scope/spi10m-n3-rx-b-IMG_0872.jpg) |
| N2 | FORCE_TX, dual-bus counter submission | **1030** | 298.22 | 260 | 208 | [IMG_0873](lab3-scope/spi10m-n2-force-tx-IMG_0873.jpg) |
<!-- spi10m-rows -->

N3 rows were captured with N3 on 124020. For FORCE_TX, the images were then swapped with pyOCD so 124020 ran N2. With the user's same-task reuse rule, N2 HB_TX, TEST_BTN and CAN_RX A/B use the N3 values above.

Effect of the faster SPI clock:

| Task | 656.25 kHz max / mean | 5.25 MHz max / mean | Handout budget |
|---|---:|---:|---:|
| CAN_RX A/B | 404–407 / 402–405 | **256–287** / 234 | 80 µs; 0.3 ms deadline |
| HB_TX | 815–826 / 815–821 | **1270** / 306 | 120 µs |
| FORCE_TX | 1050 / 924 | **1030** / 298 | 120 µs |
| TEST_BTN | 896–1240 / 892–911 | **850** / 385 | 20 µs |

CAN_RX now meets its 0.3 ms deadline. Means fell by a factor of 2.4–3.1. Transmit-task minima are 260 µs, still above the 120 µs budget. That remaining time is Zephyr MCP2515/SPI driver overhead per frame, not SPI clocking; two frames need about 46 µs of clocks. Transmit maxima did not fall and now vary widely (std dev about 145–166 µs, compared with about 1 µs before). The serial counters show the heartbeat thread's own CPU time peaks at 348 µs. The rest of the elapsed tail is preemption or blocking: driver-mutex contention with the higher-priority MCP2515 interrupt thread handling received frames, or waiting for a free TX buffer. The handout's GPIO-toggle method includes this preemption. Report the scope maxima as WCET-with-preemption and the thread CPU time as the execution estimate.

### SPI-bound tasks exceed the handout budgets (656.25 kHz build)

CAN_RX (404–407 µs vs 80 µs, deadline 0.3 ms), HB_TX (815–826 vs 120 µs), FORCE_TX (1050 vs 120 µs) and TEST_BTN (896–1240 vs 20 µs) all wait on MCP2515 SPI transfers. The overlay requests `spi-max-frequency = <1000000>`. SPI1 runs from the 84 MHz APB2 clock with power-of-two dividers. Because 84/64 = 1.3125 MHz exceeds the request, the driver uses 84/128 = **656.25 kHz**. The scope confirmed a 1.520 µs SCK period (about 658 kHz) and a 202.5 µs transaction. Even at a true 1 MHz, these tasks would still exceed the budgets (only about 1.5× faster SPI). The budgets imply multi-MHz SPI; the MCP2515 is rated to 10 MHz. The team chose to report these measured values with this explanation rather than reflash at a higher SPI rate. Non-SPI tasks are within budget.

### Workload and boundary notes

- **PID:** links the unchanged Lab 2 velocity calculation. Each 10 ms activation consumes one synthetic 20 ms encoder sample. Test phases exercise changing output and both duty clamps. FPU sharing is enabled; no physical encoder or motor output is included.
- **STEER:** links the unchanged Lab 2 `servo_map`, using tracked 1200/1600/2000 µs calibration. A dual-bus 20 ms command stream exercises center, endpoints and intermediate positions. Results are published, not applied as PWM. This is the mapping calculation, not the complete autonomous steering policy.
- **DRIVE:** remains a GPIO demonstration, not the complete Lab 2 motor driver.
- **TEST_BTN:** begins after debounce and includes fault-frame submission. It is not button-edge-to-output latency.
- **Receive dispatch:** excludes preceding ISR and MCP2515 SPI work. The separate **404 µs** capture includes elapsed time from the isolated receive INT edge through dispatch completion. It used one valid CTRL frame every 100 ms on one bus, with both MCU application transmitters paused. Do not add 24 µs to 404 µs.
- **Heartbeat and FORCE:** include two controller submissions. The requested SPI rate remains 1 MHz; the earlier diagnostic measured approximately 658 kHz. Both submissions require at least 240 SPI clocks, approximately 366 µs at 656.25 kHz, before other work.
- These rows span different builds and workloads. They are not one simultaneously measured final-application task set.

Earlier heartbeat **790 µs** and empty PID-demo **11 µs** results remain in the bring-up history, but are not substituted for the revised workloads above.

### Build keys

All archives are under the Git-ignored `logs/lab3-can/` directory and contain matching binaries/ELFs and configuration evidence:

| Key | Archive | Relevant change |
|---|---|---|
| 043636 | `20261019-043636-measurement-build/` | Working app-managed watchdog and initial task probes |
| 051047 | `20261019-051047-b1-measurement-build/` | Built-in B1/PC13 replaces external PA8 |
| 053026 | `20261019-053026-pid-rx-measurement-build/` | Real PID workload, heartbeat runtime accounting, per-bus RX markers |
| 060412 | `20261019-060412-steering-measurement-build/` | Real Lab 2 steering mapping; current MCU images |

Logical identities through the October 21 Nucleo captures were N2 on ST-LINK ending **124020** (COM6) and N3 on **171333** (COM4). After those captures, pyOCD swapped the images: N3 is now **124020** and N2 is **171333**. Rediscover ports before use. Physical wiring was not swapped. See the bring-up record for current bus-label mapping.

## Pi GPIO scope measurements

> **Superseded boundary.** These October 19 captures toggled CMD_TX before the CAN writes. The handout places CMD_TX after both writes, so these values exclude the write calls. Use the October 21 post-write captures for the report.

The bridge ran with all three threads at **SCHED_FIFO priority 1**. Laptop input was valid synthetic 276-byte UDP at nominal 20 ms intervals. GPIO17 starts a pair at the first receive in a drained batch; GPIO27 matches it immediately before command submission. Coalesced updates and stale repeats do not create unmatched edges.

The scope measured **CH1 rising → CH2 rising**:

| Load condition | Maximum | Mean | Minimum | Count | Evidence |
|---|---:|---:|---:|---:|---|
| Idle | **808 µs** | 230.20 µs | 196 µs | 1.159k | [IMG_0853](lab3-scope/pi-idle-scope-IMG_0853.jpg) |
| Four normal-priority CPU workers | **246 µs** | 118.91 µs | 106 µs | 399 | [IMG_0855](lab3-scope/pi-stress-scope-IMG_0855.jpg) |

Both selected captures use 200 µs/div and 2 V/div. A 60-second collection was requested for each; the photos do not independently establish duration. The coarse 10 ms/div [IMG_0854](lab3-scope/pi-stress-coarse-IMG_0854.jpg) result is not used in this table.

Separate software companion windows, taken before each load transition, provide percentiles for the **first UDP receive in a batch → pre-send timestamp** boundary:

| Condition | Recorded span | Records | Maximum | p99, nearest rank |
|---|---:|---:|---:|---:|
| Idle | 64.976 s | 3240 | 530.320 µs | **254.606 µs** |
| Stressed | 64.994 s | 3246 | 362.347 µs | **212.756 µs** |

These companion windows contain both edge polarities and are not identical to the scope acquisition windows. GPIO syscall/edge overhead differs from the software timestamp boundary. The p99 values are calculated from CSV samples, not inferred from the scope's mean and standard deviation.

The measured aggregate CPU busy fraction during the stressed scope phase was **99.986%**. The governor was not changed. A lower stressed mean does not imply that adding load universally improves latency.

## Pi software-only scheduling comparison

These earlier trials had GPIO tracing **disabled** and used latest-packet timing, not the later paired-batch marker boundary. Each input trial lasted 65 seconds and received all 3250 sent UDP datagrams.

The submission group includes Python message construction, both SocketCAN calls and synchronous logging inside `send_both`. It is not physical CAN delivery.

| Scheduling / load | Separate commands | Receive → pre-send max / p99 | Receive → submission-group completion max / p99 |
|---|---:|---:|---:|
| Normal scheduling, idle | 3244 | 619.137 / 334.253 µs | 1774.950 / 1240.662 µs |
| Normal scheduling, four CPU workers | 3243 | 4385.198 / 157.163 µs | 5963.539 / 4235.923 µs |
| FIFO 1, four CPU workers | 3146 | 312.698 / 123.146 µs | **477.621 / 401.066 µs** |

No CAN-send errors occurred. Latest-input coalescing combined 6, 7 and 104 UDP updates respectively; those are not counted as separate commands. The FIFO trial had no measured submission-group sample above 2 ms. Its post-collection shutdown interrupt is documented, along with verification of complete measurement data and process exit.

Stage profiling identified involuntary descheduling during long intervals with very little actual CPU time. Pinning the bridge to CPU3 did not resolve the tail and was not adopted. FIFO 1 was applied per process; the Pi kernel was not replaced with PREEMPT_RT, and future bridge launches must explicitly apply the scheduling policy.

## Evidence and current running state

Persistent evidence is rooted at:

`C:\Users\13982\18649_team4\logs\lab3-can\`

- Scope photos use descriptive names containing the IMG number.
- `20261019-061302-pi-latency/`: original software-only idle/stress CSVs, sender records, source snapshot, hashes and environment/cleanup data.
- `20261019-063643-pi-realtime-trial/`: FIFO trial, verified thread policies and complete-data validation.
- `pi-scope/`: traced bridge/sender ownership, raw CSV snapshots, companion-window summaries and load lifecycle logs. `state.json` points to the live remote CSV and stdout/crash log.
- Matching MCU ELFs and logs are in the build archives above; preserve full logged coredumps with the matching ELF if a fault occurs.

After [IMG_0855](lab3-scope/pi-stress-scope-IMG_0855.jpg), the four scope-load workers were stopped. The traced FIFO bridge and laptop UDP sender remain running at the user's request. No stress worker remains active. Use the scoped `pi-scope/stop.py` to stop only this session when required.

## Not measured or not implemented by this pass

- Physical wheel-proxy integration; these Pi tests used synthetic UDP input.
- A complete DRIVE/motor-output workload and physical servo PWM output.
- Full brake/steering hardware end-to-end latency, blinker synchronization, broader fault/recovery timing and the optional relay configuration.
- A single final-build, final-load remeasurement of every shared task on both nodes.

The task graph and response-time analysis remain outside this measurement-only request.
