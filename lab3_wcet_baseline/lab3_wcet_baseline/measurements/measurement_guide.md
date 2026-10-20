# Lab 3 Timing and Fault Measurements

Use this guide with the task/message tables in the Lab 3 handout. Record the firmware hash, Zephyr version, Pi OS/kernel, CAN bit rate, test setup, load condition, sample count, max, p99, and whether each value is **measured** or **assumed**. Never report the observed maximum as a formal WCET proof.

## Instrumentation points

### Raspberry Pi

| Probe | BCM | Meaning |
|---|---:|---|
| UDP_RX | 17 | Start one paired edge at the first `recvfrom` return in a drained UDP batch |
| CMD_TX | 27 | Match UDP_RX's level immediately after CTRL is written to can0 and can1, before logging; coalesced input/stale repeats add no unmatched edges |
| CAN_TX_A | 22 | Toggle immediately before queue/send call on `can0` |
| CAN_TX_B | 23 | Toggle immediately before queue/send call on `can1` |

`--trace-gpio` uses libgpiod v2. Confirm the lines are not owned by another process (`gpioinfo`). The GPIO markers are userspace events, not exact hardware NIC arrival/transmission edges.

### STM32, both nodes

| Probe | MCU pin | Meaning |
|---|---|---|
| CAN_RX_A | PC2 | Toggle in dispatch thread after MCP2515 driver has read/queued the frame |
| CAN_RX_B | PC3 | Same for bus B |
| CAN_TX_A | PA0 | Toggle before `can_send` on bus A |
| CAN_TX_B | PA1 | Toggle before `can_send` on bus B |
| DEG_A / DEG_B | PB0 / PB1 | Per-bus degraded indication (also probe points) |
| ERR | PC0 | High in error state |
| SRV | PC1 | N2 steering task-body marker only; no servo is driven |
| PWM_SET | PB9 | N3 drive-task body marker only; no PWM output is driven |
| DIR_A | PB10 | N3 requested-brake/error indication in demo mode |
| RELAY_TX | PC6 | N2 relay thread queues a forwarded frame on the opposite bus |
| PID | PB11 | N3 10 ms worker running Lab 2 PID on synthetic samples; no motor output |
| FL / FR | PA4 / PB8 | N2 front LEDs |
| RL / RR | PC4 / PC5 | N3 rear LEDs |
| TASK_BODY | PC8 | Selected single-worker task, configured by `timing probe NAME`; off by default |

The STM32 USB console prints named `OBS_TASK` records every five seconds, with raw-cycle maxima, upward-rounded microseconds and counts. These are **elapsed** intervals: preemption and resource waits occurring inside the body are included, while waiting before body entry is excluded. PC8 pulses provide a second observation and include end-of-sample bookkeeping. See [exact counter boundaries and limitations](../README_WCET_BASELINE.md). Both revised images are flashed and PC8 was scope-verified; current probes are on the Pi GPIO markers. See the current deployment record before comparing captures from different builds. `OBS_THREAD` separately reports heartbeat thread-accounted runtime. Bus-specific `rx_dispatch_a/b` and `timing tx off|on` support isolated receive captures; see the measurement boundaries in the linked README.

The hardware diagnostic results already collected are in [the bring-up record](../../../doc/LAB3_CAN_BRINGUP.md). They are not measurements of these application tasks.

## What to measure

1. **Pi latency (Part 3.3):** run the proxy for at least one minute with normal load, then repeat under stress. In `pi_run.csv`, `UDP_TO_CMD_TX.latency_us` starts at the latest received packet. With GPIO tracing, `UDP_BATCH_TO_CMD_TX.latency_us` starts at the first packet in the drained batch and corresponds to the paired scope markers; account for GPIO edge/syscall overhead. Report max and p99; note the logging/probe overhead.
2. **Pi CAN send duration:** `CTRL_SEND_GROUP.latency_us` measures the dual-CAN submission group, including synchronous logging; it is not physical wire time. Physical bus occupancy is calculated from the handout's 270 us worst-case 8-byte frame assumption at 500 kbit/s.
3. **STM task elapsed times:** collect `OBS_TASK` body records, per-bus RX callback/queue/dispatch records and counts. Select each available body on PC8 with `timing probe NAME`. Measure the high pulse from rising to falling edge. Keep GPIO observations separate from the event-toggle markers CAN_RX_A/B and CAN_TX_A/B. The relay requires an explicitly enabled Part 4 build. A count of zero is unmeasured.
4. **Brake/throttle E2E (2 ms):** capture Pi UDP_RX and CMD_TX, N1 CAN_TX_A, N3 CAN_RX_A, and N3 DIR_A/PWM_SET. Measure UDP_RX to requested output marker. Do not sum a stage twice if the scope already includes it.
5. **Relay path:** disconnect N1 from CAN B and N3 from CAN A. Capture N1 UDP_RX, N2 RELAY_TX (PC6), and N3 DIR_A/PWM_SET. Measure end-to-end time and compare with single-bus path.
6. **Steering (50 ms):** measure N1 UDP_RX to N2 SRV marker. The SRV marker represents processing, not physical servo movement.
7. **Blinker start and sync:** measure BLINK reception to FL/RL edges and capture FL and RL simultaneously over at least ten edges. Report maximum front/rear edge skew; do not infer a 1 ms guarantee from one edge.
8. **Test-button/error propagation:** measure the physical button edge to local ERR, then to remote ERR and hazard/brake demo output. Repeat the N2 test-button scenario and Pi wheel-button scenario.
9. **Heartbeat and degraded LEDs:** disconnect one node's A jumper and measure DEG_A assertion; restore and measure clearing. Repeat B, whole-bus loss, and both-bus isolation scenarios. Three missed 20 ms heartbeats implies a nominal 60 ms detection interval plus phase/processing delay.
10. **CPU load:** run with console output at its default rate, then reduce logging or redirect the serial output and compare. Logging can perturb measurements.

## CSV analysis

From this variant directory, `lab3_wcet_baseline/lab3_wcet_baseline`:

```sh
python3 measurements/analyze_timing.py measurements/pi_run.csv
```

The script summarizes logged events, the observed UDP-to-CMD_TX latency distribution, the send-call duration, and userspace event inter-arrivals. It cannot recover a physical wire timestamp from a `send()` return. Use scope captures for the physical chain.

Capture each STM32 USB console using your terminal application and save it as a text file, then convert the periodic software timing snapshots:

```sh
python3 measurements/parse_stm32_console.py n2_console.txt --tasks --out measurements/n2_timing.csv
python3 measurements/parse_stm32_console.py n3_console.txt --tasks --out measurements/n3_timing.csv
```
