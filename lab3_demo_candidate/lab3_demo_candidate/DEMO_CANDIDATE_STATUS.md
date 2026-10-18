# Demo candidate: changes and remaining verification

This variant builds on the original Lab 3 starter and adds two targeted behavioral changes:

1. **Per-bus-aware duplicate filtering.** A frame is suppressed as a redundant copy only when the same ID, sequence, and (for FAULT) source was seen on the opposite bus within `DUP_WINDOW_MS` (default 5 ms). A same-bus frame with the same sequence is not automatically dropped. Measure cross-bus arrival skew and adjust the window only with evidence.
2. **Fresh CTRL supervision.** After the node has reached operational state, a command stream older than 60 ms forces the node back into ERROR; recovery requires fresh CTRL and peer heartbeats.

## Still not certified demo-ready

- The firmware has **not** been compiled against your installed Zephyr SDK or flashed to either Nucleo. Device-tree bindings, MCP2515 driver support, watchdog node, pinctrl, and `can_recover()` must be verified in your environment.
- The `BLINK` payload contains an N1 monotonic timestamp, but the STM32s do not share N1's clock. This candidate does not implement clock synchronization or future-edge scheduling. Measure FL/RL skew over at least ten edges; if it exceeds 1 ms, implement and test an explicit synchronization strategy.
- Relay behavior, bus-off recovery, all R4.8 scenarios, double-press clearing, startup error-state transition, and 100 ms fault propagation still require hardware testing. The relay policy is a candidate, not a proven fault-tolerant routing protocol.
- Task bodies are still largely measured within the dispatch thread rather than all being independent periodic tasks. Match the final task graph and priorities to your Part 2 analysis before using the results as evidence.
- GPIO overlay assignments and active levels are assumptions. Confirm each one against the actual wiring and Section 5 test-point table before connecting test equipment.
- CRC-8/ATM and payload byte layouts are implementation choices. Freeze them with the team/TA before measuring protocol behavior.

## Suggested demo gate

Do not use this as the TA demo image until: (a) both zone builds succeed; (b) normal catalog traffic and sequence behavior are confirmed with `candump`; (c) normal steering/brake/blinker paths work; (d) all six R4.8 fault scenarios and recovery deadlines pass; (e) front/rear blinker skew and brake-chain timing are measured; and (f) raw logs/scope captures are saved.
