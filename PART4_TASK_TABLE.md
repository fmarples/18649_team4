# Part 4 task table: proposal, not measured firmware behavior

Source: [lab handout](doc/18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf),
Part 4, requirements table, and checkoff. This is the team's single planning
table, retained from Tianyi's integration plan in place of the older starter
template because it separates safety, actuation, ADC, and logging work and
tracks measurements explicitly. The data-exchange column retains the old
template's "talks to" information required by the handout.

The current `stm32_zephyr/src/main.c` still has its original link-only threads
and priorities, documented in [PROTOCOL.md](PROTOCOL.md#thread-responsibilities).
None of the proposed new tasks below is implemented by adding this document.

All proposed thread priorities are nonnegative/preemptible. Smaller numbers
mean higher priority in Zephyr. Confirm execution times and adjust priorities
when integrating real drivers. Drivers must not block the urgent control path.

| Work | Proposed trigger/period | Proposed thread priority | Requirement or purpose | Talks to | Measured result |
| --- | --- | --- | --- | --- | --- |
| UART receive | UART interrupt | ISR, not a thread | Capture bytes and queue candidate frames promptly | Pi UART, command queue | Pending |
| Encoder edges | Hardware counter or GPIO interrupt; driver-dependent | ISR/hardware | Count both wheels reliably; defer velocity math | Encoder inputs, count snapshots | Pending |
| Validate commands, safety state, watchdog | On received frames; watchdog checked at most every 1 ms | 0 | Publish valid commands; detect link/input/self-test faults | RX queue, shared command/safety state, actuator owners | Pending |
| Motor control and brake application | Wake on new commands/faults; periodic control every 1 ms initially | 1 | Throttle/brake effect within 2 ms from the handout STM32 test point | Command/safety state, encoders, PID, L298N | Pending |
| Status transmit | Every 20 ms | 2 | 20 ms +/-10%; report consistent state and latest valid current readings | State/current snapshots, Pi UART | Pending |
| Steering output | On commands or every 10 ms | 3 | Command-to-servo-signal response within 50 ms; clamp calibrated endpoints | Command/safety state, servo PWM | Pending |
| Blinker state/output | On commands/state changes plus scheduled edge deadlines | 4 | Response within 100 ms; normal cycle 1 s, 500 ms on/500 ms off; hazards cycle 500 ms | Wheel buttons/angle, safety state, four LED outputs | Pending |
| Current sampling | Every 20 ms initially; refine for ADC/PWM noise | 5 | Acquire calibrated samples and publish validity without delaying status TX | Three ADC channels, current snapshots | Pending |
| Debug console | Every 250 ms or slower | 6 | Human diagnostics; outside urgent paths | State snapshots, ST-LINK console | Pending |

The 1 ms motor-control period is a proposed starting point. A 2 ms response
budget also includes validation, scheduling delay, blocking, calculation, and
the actual output update. Measure the full path rather than claiming success
from the period alone. The current Part 2 CRC/link queue is the starting point
for the integration, not a completed response-time guarantee.

## Safety and synchronization decisions to finish

- Give motor outputs one owner and ensure a newer error/brake decision cannot
  be overwritten by an older drive command.
- Safety includes startup error, invalid command, link timeout, self-test
  single press, and double-press recovery. Select and document the button,
  debounce interval, and double-press interval with the team.
- Self-test response target: use the stricter 10 ms figure pending TA
  clarification (checkoff says 100 ms).
- Cable-loss response target: use 100 ms pending TA clarification (Part 2 says
  150 ms). Existing STM32 detection is configured at 80 ms, not measured here.
- Review upstream UDP freshness as well as the STM32 cable timeout before
  connecting actuation; their delays can accumulate.
- Use queues and short protected snapshots for commands/state/measurements.
  Never hold the shared-state mutex during logging or UART/ADC/driver waits.
- Document data age and validity when status reports the latest sensor sample.
