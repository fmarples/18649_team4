# Lab 3 WCET / Parts 2–4 measurement baseline

This is the instrumented starter intended for task/message timing experiments before adding demo-oriented behavioral fixes. It retains the current task bodies, GPIO probes, cycle-counter maxima, Pi CSV logger, and measurement parsers. It is a measurement baseline, **not a claim of passing the Section 5 checkoff**.

## What to measure

1. **Part 2 task WCET candidates:** on N2 measure `HB_TX`, `HB_MON`, `STEER_DRIVE`, `TEST_BTN`, `RELAY`; on N3 measure `HB_TX`, `HB_MON`, `STEER_DRIVE`, `PID`, `TEST_BTN`. `OBS_MAX_US` reports observed execution-time maxima and sample counts. These are observed maxima, not mathematical WCET proofs.
2. **Part 2 message response:** use GPIO probes and CAN analyzer/scope to measure bus arbitration/wire times; task-body timing alone does not include all release jitter, blocking, or interference.
3. **Part 3 chains:** measure Pi `UDP_RX` to `CMD_TX`, CAN TX to CAN RX, and N3 output marker (`DIR_A` / `PWM_SET`) separately. For the relay case, include `RELAY_TX`.
4. **Part 4:** repeat under single-bus loss and relay scenario, and compare the measured stage maxima to the analysis.

## Suggested collection procedure

- First confirm the exact pin map, CAN bit rate, oscillator, and message layouts. Build N2 and N3 separately.
- Run with both buses healthy and all nodes connected. Capture at least 1000 task activations where practical; also record counts and the longest observed duration.
- Repeat with realistic bus traffic, then with the handout's relay topology (N1 disconnected from B and N3 disconnected from A).
- Use `measurements/measurement_guide.md` and the CSV parsers. Keep raw CSV, console logs, and scope captures; record firmware revision, build options, load, and test conditions.
- Do not label an observed maximum as formal WCET. State whether each value is measured or assumed, and explain instrumentation overhead.

## Measurement caveats

- The existing `OBS_MAX_US` counters measure instrumented task-body elapsed time, not full RTOS response time. They omit waiting time before a thread runs and may include nested work such as mutex waits or `can_send()` calls.
- Console output every 250 ms can perturb timing. For final data, collect a short warm-up, keep logging low priority, and compare with a build that suppresses frequent console output if your analysis requires lower perturbation. Preserve sample counts.
- Pi `UDP_TO_CMD_TX` is a userspace marker latency, and `CTRL_SEND_GROUP` is the duration of two SocketCAN send calls. Neither is a physical wire timestamp. Use the scope for the actual end-to-end chains.
- This baseline intentionally retains known starter limitations in deduplication, input freshness/error-state transitions, and demo fault behavior. Use it for measurement scaffolding and comparison, not the final checkoff.

## Build selection

Build `stm32_zephyr` once for N2 and once for N3, following the main README and your installed Zephyr board naming. Firmware compilation has not been verified in this environment.
