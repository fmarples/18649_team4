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

### SPI polling mode re-measurement (October 21, build `20261021-spi-polling`)

The user requested a trial of SPI polling. The build adds `CONFIG_SPI_STM32_INTERRUPT=n` to `prj.conf`, overriding the nucleo_f401re board default. That removes the per-byte SPI interrupt and the sleep/wake per transaction. SPI remains at 5.25 MHz, with N2 on 124020 (probed) and N3 on 171333. Before/after board-counter snapshots, each taken 120 s after reset under the same bridge traffic, are in `logs/lab3-can/20261021-spi-polling/`. The heartbeat thread's CPU-time maximum fell from 356–366 µs to 246–250 µs.

| Node | Measured operation | Maximum | Mean | Min | Count | Evidence |
|---|---|---:|---:|---:|---:|---|
| N2 | HB_TX, dual-bus heartbeat submission | **790** | 186.78 | 180 | 1591 | [IMG_0875](lab3-scope/polling-n2-hb-tx-IMG_0875.jpg) |
| N2 | FORCE_TX, dual-bus counter submission | **890** | 321.44 | 170 | 597 | [IMG_0876](lab3-scope/polling-n2-force-tx-IMG_0876.jpg) |
| N2 | TEST_BTN, accepted B1 processing after debounce, including FAULT submission on both buses | **450** | 261.00 | 250 | 20 | [IMG_0877](lab3-scope/polling-n2-test-btn-IMG_0877.jpg) |
| N2 | STEER, non-SPI spot-check (Lab 2 mapping) | **9.5** | 9.4439 | 9.4 | 342 | [IMG_0878](lab3-scope/polling-n2-steer-IMG_0878.jpg) |
| N2 | CAN_RX_A, isolated INT falling to dispatch completion (CH2 PA10 → CH1 PC8 falling). Displayed min 0.0 s is one spurious pairing; std dev implies one outlier | **183** | 180.93 | 0.0 (spurious) | 162 | [IMG_0879](lab3-scope/polling-n2-rx-a-IMG_0879.jpg) |
| N2 | CAN_RX_B, isolated INT falling to dispatch completion (CH2 PB5 → CH1 PC8 falling) | **182** | 181.04 | 181 | 326 | [IMG_0881](lab3-scope/polling-n2-rx-b-IMG_0881.jpg) |
<!-- polling-rows -->

Under the user's reuse rule, N3 HB_TX, TEST_BTN and CAN_RX A/B use these N2 values. One non-SPI check (STEER) is unchanged by polling. The PID, HB_MON, BLINK and DRIVE rows were not re-captured.

| Task | Interrupt mode, 5.25 MHz: max / mean | Polling, 5.25 MHz: max / mean | Handout budget |
|---|---:|---:|---:|
| CAN_RX A/B | 256–287 / 234 | **182–183 / 181** | 80 µs; 0.3 ms deadline |
| HB_TX | 1270 / 306 | **790 / 187** (min 180) | 120 µs |
| FORCE_TX | 1030 / 298 | **890 / 321** (min 170) | 120 µs |
| TEST_BTN | 850 / 385 | **450 / 261** | 20 µs |
| STEER (control) | 9.8 / 9.68 | 9.5 / 9.44 | 50 µs |

Polling improved every maximum and every SPI-task mean except FORCE_TX's mean. FORCE_TX fires every 50 ms and coincides with the 20 ms heartbeat every 100 ms. During those overlaps it now waits behind a heartbeat that busy-waits instead of sleeping. Minimum transmit times (170–180 µs for two frames) remain above the 120 µs placeholder; about 46 µs of that is SPI clocking. The rest is Zephyr MCP2515 driver work per frame: mutex, TX-buffer selection, and two SPI transactions with chip-select handling. The polling build remains deployed on both boards.

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

## Demo build: clarification measurements #1–#6 (October 23)

Taken on the flashed `lab3_demo` spec-audited build with the October 22 clarification's start/stop boundaries. These supersede the measurement-firmware rows above for the report. Scope: Agilent DSO7012B, CH1/CH2 at 2 V/div, trigger 1.5 V. Probe positions: `.local-notes/lab3-scope-measurements.html` (local). Originals: `logs/lab3-can/20261023-demo-scope/`.

| # | Node | Start → stop | Max | Mean | Min | Count | Evidence |
|---|---|---|---:|---:|---:|---:|---|
| 1 | N1 (Pi) | UDP_RX rising (CH1, row 3) → CMD_TX rising (CH2, row 4), after the first CAN write; **Logitech wheel traffic** (report value) | **995 µs** | 310.59 µs | 230 µs | 1309 | [IMG_0893](lab3-scope/demo-1-pi-stage-wheel-IMG_0893.jpg) |
| 1 (supplementary) | N1 (Pi) | Same boundary, laptop synthetic UDP sender | 1885 µs | 361.42 µs | 215 µs | 972 | [IMG_0892](lab3-scope/demo-1-pi-stage-IMG_0892.jpg) |
| 2 | N3 | CAN A INT falling (CH2, CN10-33/PA10) → CAN_RX_A toggle (CH1, row 3); N3 `timing tx off`, N3 off bus B; trigger on CH1. Run 1 rising toggles, run 2 falling | **202.0 µs** (run 2; run 1 201.0) | 137.45 / 137.21 µs | 136.5 µs | 20040 / 2901 | [IMG_0900](lab3-scope/demo-2-n3-can-rx-fall-IMG_0900.jpg), [IMG_0897](lab3-scope/demo-2-n3-can-rx-rise-IMG_0897.jpg) |
| 3 | N3 | CAN_RX_A toggle (CH1, row 3) → DIR_A falling on a brake frame (CH2, row 11); wheel brake pumped; N3 TX on, N3 off bus B; trigger CH2 falling; 20 µs/div, delay −95 µs (screen −195…+5 µs excludes the previous frame's toggle); both toggle polarities measured at once | **89.4 µs** | 89.07 / 89.13 µs | 87.8 µs | 36 + 24 | [IMG_0903](lab3-scope/demo-3-n3-drive-IMG_0903.jpg) |
| 4 | N3 | Bus-A module CS (CH1, CN10-17/PB6) low width, −Width statistics; normal traffic, N3 on both buses, TX on; 10 µs/div, delay +40 µs; the run spans N2 `timing tx off` | **80.2 µs** | 46.71 µs | 4.9 µs | 15110 | [IMG_0905](lab3-scope/demo-4-n3-spi-cs-IMG_0905.jpg) |
| 5 | N2 | CAN A INT falling (CH2, CN10-29/PB5; N2 is `swap_ab`, so bus A is the CS PC7/INT PB5 module) → CAN_RX_A toggle (CH1, row 3); N2 `timing tx off`, N2 off bus B; trigger CH1 either edge, both polarities at once; 50 µs/div, delay −200 µs | **201.5 µs** | 138.40 / 138.56 µs | 135.0 µs | 3210 + 3271 | [IMG_0906](lab3-scope/demo-5-n2-can-rx-IMG_0906.jpg) |
| 6 | N2 | CAN_RX_A toggle (CH1, row 3) → RELAY_TX toggle after the bus-B send returns (CH2, row 12); scenario (c): N1 off B, N3 off A; N3 TX off so RELAY_TX marks only N1→B relays. Scope: trigger CH2 rising, 100 µs/div, delay −464 µs (screen ≈ −964…+36 µs), Δ(1↓→2↑) and Δ(1↑→2↑). Firmware cross-check: cycle counter from the dispatch start (CAN_RX_x toggle) to just after the RELAY_TX toggle, per forwarded frame | **963 µs** (scope; firmware 940 µs) | n/a (scope mean/min include mispairs) | n/a | 798 + 1051 (scope); 7300 + ~13 000 (firmware) | [IMG_0909](lab3-scope/demo-6-n2-relay-IMG_0909.jpg); firmware `logs/lab3-can/20261023-095456-demo-build-relay-c-timer2/console-130s.log` |

#1 conditions: cockpit under FIFO 1 (session `demo-d666ff66…`, Pi PID 3332 for the wheel run); markers are Python libgpiod toggles; UDP over Wi-Fi from the laptop. 500 µs/div with the trigger at center, so stop edges up to 2.5 ms are on screen. The photos do not establish the 60 s duration; 1309 rising edges at about 25/s is about 52 s. The synthetic run's 1.885 ms tail (std dev 206 µs) did not recur with wheel traffic (std dev 73 µs); both are Linux scheduling without a bound, so the report should state which run it uses and why.

#6 note: N2 relays every bus-A frame in this setup, so CAN_RX_A and RELAY_TX stay in phase, and relays overlap when frames arrive back to back. Scope Δ statistics pair a RELAY_TX edge with the nearest CAN_RX_A edge, so they cannot attribute overlapping relays; the 380 µs screen excluded every relay longer than that. The firmware `relay_c_us` counter (build `20261023-095456-demo-build-relay-c-timer2`) measures each forwarded frame between the same two boundaries. Long relays wait for one of the MCP2515's three bus-B TX buffers behind N2's own HB/FORCE frames and earlier relays (about 250 µs per queued frame on the wire). With this RELAY C the relayed brake chain exceeds 2 ms. With N3 transmitting again (full scenario (c), relays in both directions), the same counter reached 1197 µs; that includes B→A relays of N3's frames, which are outside #6's CAN_RX_A boundary. Checkoff step 7 LEDs were verified in that state: DEG_B on N1, DEG_A on N3, no DEG on N2, no zone in error, N3 following the wheel through the relay.

### Brake-chain verdicts from these measurements

Stage sums with the measured maxima above and the clarification's fixed CTRL bus term (270 µs frame + 270 µs blocking per hop). These are measured-input sums, not the report's full RTA; interference terms only add to them.

| Chain (deadline 2 ms) | Stages | Sum | Verdict |
|---|---|---:|---|
| Brake/throttle, direct | Pi 995 + CTRL on A 540 + CAN_RX N3 202 + DRIVE 89 | ≈ 1826 µs | Borderline; RTA terms may push it over |
| Brake/throttle, relayed (scenario c) | Pi 995 + CTRL on A 540 + CAN_RX N2 202 + RELAY 963 + CTRL on B ≥ 540 + CAN_RX N3 202 + DRIVE 89 | ≈ 3531 µs | **Misses** |

Why the relayed chain misses: the two CAN hops (≥ 1080 µs) plus the Pi stage max (995 µs) already exceed 2 ms before any MCU work, so it misses even with RELAY = 0 (≈ 2568 µs). The Pi max is Linux scheduling on a non-PREEMPT_RT kernel with Python GPIO toggles (typical 310 µs). RELAY's 963 µs (firmware 940 µs) is waiting for one of the MCP2515's three bus-B TX buffers behind N2's own HB/FORCE frames and earlier relays.

What would fix it: (1) bound the Pi stage near its typical value: PREEMPT_RT kernel, CPU isolation for the cockpit, or a C cockpit; (2) relay ahead of N2's own traffic: reserve an MCP2515 TX buffer (or use its TX priority bits) for relayed frames so RELAY stays near its 160–200 µs base; (3) fewer CAN hops on the brake path is not available, since scenario (c) requires the relay. Meeting 2 ms needs both (1) and (2): Pi ≤ about 300 µs and RELAY ≤ about 130 µs.

### Fault-injection matrix timing (R4.8, October 23)

Single-shot captures (trigger mode Normal, Single) on the relay-gate N2 build, wheel traffic, all nodes transmitting. Start reference is the node's CAN_RX_x test point: the last toggle before DEG/ERR rises is the last frame received on that bus; the first toggle after a gap is the first frame after the jumper is restored. Times are cursor ΔX read on the scope. DEG LEDs are re-evaluated on a received CTRL or the 20 ms HB_MON tick, not on every frame, so restore times range from tens of µs to about 20 ms. Required by the Lab 3 handout's report deliverables ("Fault-injection matrix (R4.8 a-f): expected state of each zone and LED, measured recovery time"; the clarification leaves this unchanged); pull timings support checkoff step 5. Requirements: R4.7 DEG on after 60 ms without traffic, DEG off within 100 ms of traffic resuming; R4.8(d) system error within 100 ms; R4.8(f) normal within 500 ms without reset.

| Scenario | Node | Event | Start → stop | Measured | Requirement | Evidence |
|---|---|---|---|---:|---|---|
| (a) pull | N3 | Bus-A wires pulled | last CAN_RX_A toggle (CH1, row 3) → DEG_A rising (CH2, row 7) | **60.6 ms** | DEG on after 60 ms without traffic | [IMG_0912](lab3-scope/matrix-a-n3-pull-deg-a-IMG_0912.jpg) |
| (a) restore (also f) | N3 | Bus-A wires replugged | first CAN_RX_A toggle (CH1, row 3) → DEG_A falling (CH2, row 7) | **14 ms** | ≤ 100 ms | [IMG_0910](lab3-scope/matrix-a-n3-restore-deg-a-IMG_0910.jpg) |
| (b) pull | N3 | Bus-B wires pulled | last CAN_RX_B toggle (CH1, row 4) → DEG_B rising (CH2, row 8) | **60.4 ms** | DEG on after 60 ms without traffic | [IMG_0913](lab3-scope/matrix-b-n3-pull-deg-b-IMG_0913.jpg) |
| (b) restore (also f) | N3 | Bus-B wires replugged | first CAN_RX_B toggle (CH1, row 4) → DEG_B falling (CH2, row 8) | **1.8 ms** | ≤ 100 ms | [IMG_0914](lab3-scope/matrix-b-n3-restore-deg-b-IMG_0914.jpg) |
| (a) restore, second sample | N3 | Bus-A wires replugged after the Pi and N2 had already rejoined A (meant as (e), but the last step is identical to (a)) | first CAN_RX_A toggle → DEG_A falling, zoomed to 100 µs/div on the stopped capture | **43 µs** | ≤ 100 ms | [IMG_0916](lab3-scope/matrix-a-n3-restore-zoom-IMG_0916.jpg) |
| (e) pull | all | Bus-A wires of N1, N2, N3 pulled | state read from N2/N3 consoles and the cockpit STATUS line | operational on B | DEG_A on all three, no zone in error, no hazards | console/STATUS (no capture) |
| (e) restore (also f) | N3 | All three off A; N3 replugged first (alone on A), then N2 replugged: bus A comes back; Pi replugged last | first CAN_RX_A toggle on N3 (CH1, row 3) → DEG_A falling (CH2, row 7) | **3.2 ms** | ≤ 100 ms | [IMG_0918](lab3-scope/matrix-e-n3-bus-a-back-IMG_0918.jpg) |
| (c) restore (also f) | N3, N1 | Scenario (c) (N1 off B, N3 off A, N2 relaying); N3's bus-A wires replugged, then the Pi's bus-B wires | first CAN_RX_A toggle on N3 (CH1, row 3) → DEG_A falling (CH2, row 7) | **2.2 ms** | ≤ 100 ms | [IMG_0919](lab3-scope/matrix-c-n3-restore-deg-a-IMG_0919.jpg) |
| (d) isolate | N3 → N2 | N3 already off A; N3's bus-B wires pulled | last CAN_RX_B toggle on N3 (CH1, N3 row 4; the cut happens after this frame) → N2 ERR rising (CH2, N2 row 13) | **74.4 ms** (upper bound for pull → system error) | system error ≤ 100 ms | [IMG_0920](lab3-scope/matrix-d-n3-isolated-n2-err-IMG_0920.jpg) |
| (d) restore, others | N2 | N3's bus-B wires replugged (A still out) | N2 ERR falling (CH2, N2 row 13) vs N3's first CAN_RX_B toggle (CH1, N3 row 4) | **N2 clears 320 µs before N3 receives its first frame** | normal ≤ 500 ms | [IMG_0921](lab3-scope/matrix-d-restore-n2-err-first-IMG_0921.jpg) |
| (d) restore, isolated node | N3 | N3 re-isolated, then bus-B wires replugged (A still out) | first CAN_RX_B toggle on N3 (CH1, N3 row 4) → N3 ERR falling (CH2, N3 row 14) | **17.6 ms** (plus the sub-ms gap from contact to N3's first received frame) | normal ≤ 500 ms, no reset | [IMG_0922](lab3-scope/matrix-d-restore-n3-err-IMG_0922.jpg) |

### Demo photo log

Every photo taken in this pass, archived in `logs/lab3-can/20261023-demo-scope/`. Only **Report** photos go in the write-up.

| Photo | Measurement | Status | Note |
|---|---|---|---|
| IMG_0892 | #1 Pi stage, synthetic sender | Supplementary | Max 1885 µs |
| IMG_0893 | #1 Pi stage, wheel traffic | **Report** | Max 995 µs |
| IMG_0894 | #2 CAN_RX N3, run 1, Δ(2↓→1↑) triggered on INT | Rejected | Min −290.5 µs, max 327.5 µs. The DSO7000B Delay uses the edges closest to the trigger point, so triggering on INT paired other frames' toggles. Retake triggers on CAN_RX_A |
| IMG_0895 | #2 CAN_RX N3, run 1, Δ(2↓→1↑), trigger CH1 rising, delay −200 µs; N3 TX off, bus B connected | Supplementary | Max 386.0 µs, mean 192.62, min 137.0, count 1324. Back-to-back INT pulses: includes queueing behind other frames. Retake with N3 off bus B |
| IMG_0897 | #2 CAN_RX N3, run 1 (CAN_RX_A rising), Δ(2↓→1↑), trigger CH1 rising; N3 TX off and off bus B | **Report** | Max 201.0 µs, mean 137.21, min 136.5, std dev 2.61, count 2901. During this run bus B was also down between the Pi and N2 (both error-passive); bus A, which this measures, was unaffected |
| IMG_0900 | #2 CAN_RX N3, run 2 (CAN_RX_A falling), Δ(2↓→1↓), trigger CH1 falling; N3 TX off and off bus B; N2 relay-gate build | **Report** | Max 202.0 µs, mean 137.45, min 136.5, std dev 3.60, count 20.04k |
| IMG_0901 | #3 DRIVE N3, run 1, Δ(1↑→2↓), trigger CH2 falling | Supplementary | Max 333.5 µs, mean 104.94, min 89.0, std dev 59.8, count 32. Typical 89 µs; the max ≈ 89 + one frame time (~245 µs), a mispair with the previous frame's toggle (see IMG_0902); superseded by IMG_0903 |
| IMG_0902 | #3 DRIVE N3, run 2, Δ(1↓→2↓), trigger CH2 falling | Supplementary (pairing evidence) | Max 333.5 µs, mean 103.95, min 89.0, count 33. Current capture shows the wrong pair: previous frame's CAN_RX_A falling edge at −331 µs, the brake frame's own rising toggle at about −90 µs. Both #3 maxima are mispairs (89 µs + one frame time); retake with the measurement window restricted to a −195…+5 µs zoom |
| IMG_0903 | #3 DRIVE N3, both polarities at once: Δ(1↓→2↓) and Δ(1↑→2↓), 20 µs/div, delay −95 µs | **Report** | Max 89.4 / 89.2 µs, mean 89.07 / 89.13, min 87.8 / 89.0, count 36 / 24 (one per brake press). The DSO7000B measures displayed data only, so the narrow screen prevents the earlier mispairs |
| IMG_0904 | #4 SPI frame load (B), N3 bus-A CS −Width | Supplementary (same run, earlier) | Max 67.9 µs, mean 47.97, min 11.8, std dev 5.91, count 2808. SPI1 5.25 MHz in polling mode: about 21 µs of clock per 14-byte transfer plus per-byte driver polling; the tail is interrupts during a transaction |
| IMG_0905 | #4 SPI frame load (B), same run continued | **Report** | Max 80.2 µs, mean 46.71, min 4.9, std dev 6.36, count 15.11k. Includes the traffic change when N2 TX was switched off for #5 |
| IMG_0906 | #5 CAN_RX N2, Δ(2↓→1↓) and Δ(2↓→1↑), trigger CH1 either | **Report** | Max 201.0 / 201.5 µs, mean 138.56 / 138.40, min 135.0, std dev 9.6 / 9.9, count 3271 / 3210. The leftover −Width(1) line from #4 shows no edges and is unused |
| IMG_0907 | #6 RELAY N2, scenario (c) (N1 off B, N3 off A), N3 TX off; Δ(1↓→2↑) and Δ(1↑→2↑), trigger CH2 rising, 100 µs/div, delay −400 µs | Rejected | Max 882 / 893 µs, mean 199.5 / 758.8, min 164 / 134, count 1404 / 76. Every bus-A frame is relayed, so the two toggles stay in phase; the 900 µs screen admits the previous frame's toggle and the maxima are mispairs. Retake at 50 µs/div, delay −130 µs |
| IMG_0908 | #6 RELAY N2, Δ(1↓→2↑) and Δ(1↑→2↑), 50 µs/div, delay −130 µs | Supplementary (window-limited) | Max 377.0 µs, mean 182.19, std dev 34.0, count 2184 (Δ(1↑→2↑): 14 samples of later-frame pairs, max 158.5). Every bus-A frame is relayed, so the toggles stay in phase. The max lies at the 380 µs screen edge: a relay over 380 µs would be uncounted |
| IMG_0909 | #6 RELAY N2, Δ(1↓→2↑) and Δ(1↑→2↑), trigger CH2 rising, 100 µs/div, delay −464 µs | **Report** | Max 963 / 962 µs, count 798 / 1051. Mean and min (−35, 0.0 µs) include mispairs of overlapping relays; the max agrees with the firmware per-frame counter (940 µs, same boundaries) |
| IMG_0910 | Matrix (a)/(f): N3 bus-A restore, Single, 10 ms/div, delay −40 ms, cursors | **Report** | ΔX 14 ms from first CAN_RX_A toggle to DEG_A fall |
| IMG_0912 | Matrix (a): N3 bus-A pull, Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 60.6 ms from last CAN_RX_A toggle to DEG_A rise |
| IMG_0913 | Matrix (b): N3 bus-B pull, Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 60.4 ms from last CAN_RX_B toggle to DEG_B rise |
| IMG_0914 | Matrix (b): N3 bus-B restore, Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 1.8 ms from first CAN_RX_B toggle to DEG_B fall |
| IMG_0915 | Same capture as IMG_0916 at 20 ms/div; cursors still at the IMG_0914 values | Rejected (stale cursors) | — |
| IMG_0916 | N3 bus-A restore after Pi and N2 rejoined, zoomed 100 µs/div, cursors | Supplementary ((a)-type, not (e)) | ΔX 43 µs from first CAN_RX_A toggle to DEG_A fall |
| IMG_0918 | Matrix (e): bus A back (N3 first, then N2), Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 3.2 ms from N3's first CAN_RX_A toggle to DEG_A fall; regular toggling follows |
| IMG_0919 | Matrix (c): N3 bus-A restore while N1 off B, Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 2.2 ms. During (c) N2 relayed about 9,750 frames with one failure. While the Pi's bus-B wires were being replugged, the cockpit logged DEG_B flapping about 30 times over 10.5 s (Pi uptime 25066.4–25077.0), only on B, with ENOBUFS TX errors and error-passive transitions but no bus-off; consistent with intermittent contact during insertion. Stable since |
| IMG_0920 | Matrix (d): N3 isolated (B pulled after A), CH1 N3 row 4, CH2 N2 row 13, Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 74.4 ms from N3's last received bus-B frame to N2 ERR rise (66 ms heartbeat timeout plus the next HB_MON tick) |
| IMG_0921 | Matrix (d) restore: CH2 N2 ERR, CH1 N3 CAN_RX_B, 2 ms/div, cursors | **Report** | ΔX −320 µs: N2 leaves error before N3 receives anything. N3's MCP2515 sends its queued HB_N3/FAULT frames by itself the instant the wire connects; N2 records the heartbeat and the FAULT triggers an immediate re-evaluation. N3's first CAN_RX_B toggle is therefore not the reconnect instant; N3's own ERR is the slowest recovery |
| IMG_0922 | Matrix (d) restore: CH1 N3 CAN_RX_B, CH2 N3 ERR, Single, 20 ms/div, delay −80 ms, cursors | **Report** | ΔX 17.6 ms. N3 leaves error once both peers are alive and the next CTRL or HB_MON tick re-evaluates; this is the slowest node, so system recovery from (d) is about 18 ms |

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
