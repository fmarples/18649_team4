# Future three-zone CAN integration — draft for team review

This is a proposed next-stage design, not implemented Lab 2 behavior. Check it
against your Lab 1 zone assignments and message-ID rules before submitting.
Today one Nucleo owns the outputs and receives CRC UART commands from the Pi.

| Proposed zone | Functions moved there | State crossing the CAN boundary |
| --- | --- | --- |
| Front | Steering, front-left/front-right lamps, validated driver-intent coordinator | Requested speed/brake/steer, selected turn mode, global error/self-test epoch |
| Rear-left | Left motor driver/encoder/current and rear-left lamp | Left measured speed/current, local faults, command freshness |
| Rear-right | Right motor driver/encoder/current and rear-right lamp | Right measured speed/current, local faults, command freshness |

The present `drive_input`, button/self-test state, blinker phase and current
snapshots become versioned messages instead of mutex-protected in-memory
copies. Keep one output owner per zone. Each zone checks sequence numbers and
command age locally; a front-zone failure cannot leave old throttle running
indefinitely. Clearing manual self-test must not clear a real local fault.

Proposed standard 11-bit arbitration IDs: safety/fault command `0x080`, driver
intent `0x100`, blink synchronization `0x180`, and zone status `0x200..0x202`.
Lower IDs arbitrate first ([Zephyr CAN documentation](https://docs.zephyrproject.org/latest/hardware/peripherals/can/controller.html)). These are a draft priority scheme, not measured bus
response times. Assign a single publisher per ID on each bus. Pack payloads
explicitly with units, counter/version and validity; do not transmit a compiler
struct or assume the current 28/56-byte UART frames fit one classic CAN frame.

For dual CAN, use a shared command epoch/counter across paths; receivers deduplicate
copies and reject old/replayed state. Define bus-failure and conflicting-copy
behavior before enabling control. Losing both valid command paths requests the
local safe output. Do not add current trips until a later lab specifies them.

Blinker halves now have independent MCU clocks. Sending "toggle now" every
half-cycle accumulates bus jitter and can drift. Send mode plus a synchronized
phase epoch, use a monotonic local schedule, and periodically correct clock/phase
offsets. Measure front/rear skew after splitting zones; the current single-MCU
result does not establish distributed synchronization.

Integration steps: define message catalog and freshness rules; implement and
bench-test local output owners; add priority-aware transmit queues and duplicate
handling; then repeat brake/steering/blinker timing while loading both buses and
injecting link/node failures. Final IDs, payloads, periods and time-sync method
need team agreement and bus-budget calculations.
