# Lab 3 measured timing results

Selected bench results from October 19, 2026. This is a measurement ledger, not a task graph or a schedulability analysis. Detailed evidence, workload changes and deployment history are in [LAB3_CAN_BRINGUP.md](LAB3_CAN_BRINGUP.md).

## STM32 scope measurements

Times are microseconds. Node names are the logical roles **at measurement time**; the firmware roles were subsequently swapped without moving the probes. All task-body values include the work between the selected PC8 edges.

| Logical node | Measured operation | Maximum | Mean | Count | Build | Evidence |
|---|---|---:|---:|---:|---|---|
| N3 | Heartbeat TX, dual-bus submission | **815** | 814.69 | 585 | 053026 | IMG_0845 |
| N3 | Heartbeat monitor | **19** | 19 | Not supplied | 043636 | User report |
| N3 | Application receive dispatch only | **24** | 23.503 | 965 | 043636 | IMG_0843 |
| N3 | Blinker body | **15** | 15 | Not supplied | 043636 | User report |
| N3 | Real Lab 2 PID calculation on synthetic samples | **18.8** | 14.5 | Not supplied | 053026 | User report |
| N3 | Built-in B1 accepted-press processing | **1240** | 911.00 | 10 | 051047 | IMG_0844 |
| N3 | DRIVE GPIO demo, braking/error branch | **12** | Not supplied | Not supplied | 051047 | User report |
| N3 | Isolated CAN A INT assertion to dispatch completion | **404** | 402.08 | 158 | 053026 | IMG_0848 |
| N2 | FORCE_TX, dual-bus counter submission | **1050** | 924.46 | 202 | 053026 | IMG_0850 |
| N2 | Real Lab 2 calibrated steering mapping | **9.8** | 9.6768 | 518 | 060412 | IMG_0851 |

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

Current logical identities are N2 on ST-LINK ending **124020**, last COM6, and N3 on **171333**, last COM4. Rediscover ports before use. Physical wiring was not swapped. See the bring-up record for current bus-label mapping.

## Pi GPIO scope measurements

The bridge ran with all three threads at **SCHED_FIFO priority 1**. Laptop input was valid synthetic 276-byte UDP at nominal 20 ms intervals. GPIO17 starts a pair at the first receive in a drained batch; GPIO27 matches it immediately before command submission. Coalesced updates and stale repeats do not create unmatched edges.

The scope measured **CH1 rising → CH2 rising**:

| Load condition | Maximum | Mean | Minimum | Count | Evidence |
|---|---:|---:|---:|---:|---|
| Idle | **808 µs** | 230.20 µs | 196 µs | 1.159k | IMG_0853 |
| Four normal-priority CPU workers | **246 µs** | 118.91 µs | 106 µs | 399 | IMG_0855 |

Both selected captures use 200 µs/div and 2 V/div. A 60-second collection was requested for each; the photos do not independently establish duration. The coarse 10 ms/div IMG_0854 result is not used in this table.

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

After IMG_0855, the four scope-load workers were stopped. The traced FIFO bridge and laptop UDP sender remain running at the user's request. No stress worker remains active. Use the scoped `pi-scope/stop.py` to stop only this session when required.

## Not measured or not implemented by this pass

- Physical wheel-proxy integration; these Pi tests used synthetic UDP input.
- A complete DRIVE/motor-output workload and physical servo PWM output.
- Full brake/steering hardware end-to-end latency, blinker synchronization, broader fault/recovery timing and the optional relay configuration.
- A single final-build, final-load remeasurement of every shared task on both nodes.

The task graph and response-time analysis remain outside this measurement-only request.
