# Demo candidate: changes and remaining verification

This variant builds on the original Lab 3 starter:

1. **Relay-aware duplicate filtering.** The Pi and STM32s suppress matching source/ID/sequence copies on either bus using a bounded 5 ms history. This includes native and relayed copies arriving on the same bus. Measure maximum copy skew and sequence reuse before relying on that window.
2. **Fresh CTRL supervision.** After the node has reached operational state, a command stream older than 60 ms forces the node back into ERROR; recovery requires fresh CTRL and peer heartbeats.
3. **Immediate N2 forwarding.** The relay no longer waits for a 60 ms heartbeat timeout. It submits a valid foreign frame to the opposite bus unless a copy there is already known. See [relay policy and verification](RELAY_POLICY.md) for duplicate handling, timing changes and scope limitations.

## Still not certified demo-ready

- Both N2 and N3 built successfully with Zephyr 4.3.0 / SDK 0.17.4 on 2026-10-18. The production C history module passed 104 checks; all 18 Python tests passed. See [verification details](RELAY_POLICY.md).
- The updated firmware has not been flashed or checked on physical hardware. Build results alone do not verify pin wiring, bus-off recovery or deadlines. The optional `can_recover()` API is guarded; the Zephyr 4.3 MCP2515 driver does not advertise manual recovery.
- The `BLINK` payload contains an N1 monotonic timestamp, but the STM32s do not share N1's clock. This candidate does not implement clock synchronization or future-edge scheduling. Measure FL/RL skew over at least ten edges; if it exceeds 1 ms, implement and test an explicit synchronization strategy.
- Relay behavior, bus-off recovery, all R4.8 scenarios, double-press clearing, startup error-state transition, and 100 ms fault propagation still require hardware testing. The relay policy is a candidate, not a proven fault-tolerant routing protocol.
- Task bodies are still largely measured within the dispatch thread rather than all being independent periodic tasks. Match the final task graph and priorities to your Part 2 analysis before using the results as evidence.
- GPIO overlay assignments and active levels are assumptions. Confirm each one against the actual wiring and Section 5 test-point table before connecting test equipment.
- CRC-8/ATM and payload byte layouts are implementation choices. Freeze them with the team/TA before measuring protocol behavior.

## Suggested demo gate

Do not use this as the TA demo image until: (a) both zone builds succeed; (b) normal catalog traffic and sequence behavior are confirmed with `candump`; (c) normal steering/brake/blinker paths work; (d) all six R4.8 fault scenarios and recovery deadlines pass; (e) front/rear blinker skew and brake-chain timing are measured; and (f) raw logs/scope captures are saved.
