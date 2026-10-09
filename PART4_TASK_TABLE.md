# Part 4 task table: implemented schedule, hardware measurements pending

This table describes the integrated firmware now on `main`, not the earlier proposed thread split.
Tianyi reports Parts 3.3 and 3.4 tested individually. Combined-board behavior
and scope measurements remain pending. Part 3.5 ADC acquisition is implemented;
physical calibration and sensor tests remain pending.
Requirements come from the [handout](doc/18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf),
Part 4, the requirements table and checkoff.

All application threads are **preemptible**. Smaller priority numbers run first.
Priorities and periods live in `stm32_zephyr/src/schedule.h`; main priority is
`CONFIG_MAIN_THREAD_PRIORITY=1` in `stm32_zephyr/prj.conf`. A build assertion in
`main.c` requires owner < status < current workqueue < console. Interrupts can
preempt every application thread; short spinlock/driver critical sections
temporarily mask interrupts and must be included in measured latency.

| Work/context | Trigger or period actually implemented | Priority | Deadline / requirement | Talks to | Hardware measurement |
| --- | --- | --- | --- | --- | --- |
| Pi UART RX ISR | Bytes arrive; complete candidate every 28 bytes | ISR | Queue promptly; included in command-to-output response | USART1, fixed 8-frame queue, CMD_RX marker | Pending |
| Encoder GPIO ISR | Each A/B edge, x4 decoding | ISR | Count edges before another transition is missed | PB3/PA8/PB5/PA7, spinlock-protected counts | Pending combined load |
| B1 GPIO ISR | Button press edge | ISR | Latch local stop; owner applies it | Atomic B1 latch, motor owner | Pending |
| USB console RX ISR | USART2 bytes | ISR | Queue bounded bytes; no command parsing here | 256-byte queue, overflow flag | Pending |
| Status timer callback | Every 20 ms | Timer interrupt context | Signal status thread; no serialization/transmission here | Binary semaphore, maximum count 1 | Pending |
| Command validation, errors and motor outputs | One owner: wakes on queue data; waits up to 1 tick (1 ms) when empty | Thread 1 | Throttle/brake output response <=2 ms after complete command; A self-test uses the command-loss watchdog below | RX queue, CRC/ranges, shared state, PID, L298N | Pending |
| Encoder velocity / PID feedback | 20 ms actual elapsed-time sampling inside owner; command changes also update proportional output immediately | Same thread 1 | Feedback period is not the 2 ms pedal response deadline | Counts, velocity controller, motor output | Pending |
| Command-loss watchdog | Checked each owner iteration; threshold 60 ms | Same thread 1 | Three missed 20 ms updates; checkoff fail-safe <=100 ms | Last accepted reception time, actuator policy | Pending |
| Steering | Each owner iteration; hardware PWM period 20 ms | Same thread 1, after motor update | <=50 ms command-to-servo-signal change | Wheel angle, calibration, fault state, TIM4/PB9 | Pending combined load |
| Blinkers | Each owner iteration using elapsed phase; 500 ms normal half-cycle / 250 ms hazard half-cycle | Same thread 1, after motor update | <=100 ms response; 1 Hz +/-10%, 50% duty; front/rear <=1 ms skew | Buttons, angle, fault state, four GPIOs | Pending scope |
| Status TX | Semaphore from 20 ms timer | Thread 2 | Physical status period 20 ms +/-10% | Short state/current snapshots, USART1 TX | Pending scope |
| Current acquisition work item | Delayed work on a **dedicated** queue, 20 ms nominal; skips missed slots | Workqueue thread 3 | Proposed sampling cadence; no assignment-specific ADC deadline supplied | ADC1 channels 0/1/8, eight-scan mean, private current cache, status TX | Acquisition duration/noise pending |
| USB replies and diagnostics | Check queued replies every 10 ms between output bursts; diagnostics every 250 ms or slower | Thread 4 | Best effort; cannot block urgent threads for a whole print line | Reply queue, state snapshot, USART2 TX | Pending stress test |

The 1 ms wait is **not** a proven maximum execution interval. Queue backlog,
CRC, interrupts, lock contention, PID, driver calls and console parsing all
consume time. A mode change in the motor driver retains a 100 us busy wait
with interrupts enabled. Measure the complete path; do not substitute the
20 ms PID sample period or a successful build for response-time evidence.

## Answers to the Part 4 questions

**Thread, work item, timer callback, ISR:** the control thread owns decisions
and all actuator writes. The independent status thread serializes/transmits.
The current work item waits for ADC conversions on its own queue;
it cannot occupy the system workqueue or the motor owner. The periodic timer
only gives a semaphore. UART ISRs copy bytes and enqueue with `K_NO_WAIT`;
encoder ISRs update counts; B1 sets an atomic latch. Neither ISR path prints,
allocates memory, sleeps, nor waits for a mutex.

**What preempts what:** owner 1 preempts status 2, current 3, console 4. Status
preempts current/console. Steering and lamps are bounded operations within the
same owner, with motors serviced first; there is no slower-priority task that
can later overwrite a new brake decision. Separate threads for every LED or
actuator are unnecessary. `CONFIG_PRINTK_SYNC=n` avoids disabling interrupts
for a complete console line; the console UART's per-byte register access still
has short critical sections. All normal runtime printing is in thread 4.

**How state moves safely:** `k_msgq` copies complete UART candidates and servo
replies; `state_mutex` protects command/diagnostic snapshots; `current_mutex`
protects complete sample snapshots. Locks are released before UART output,
logging, actuator writes and ADC waits. Encoder counts use `k_spinlock` for a
short ISR/thread snapshot. Overflow and B1 events use atomics. A semaphore
signals status readiness. `volatile` is not used as a substitute for these.

**Timer and work backlog:** the status semaphore holds at most one pending
event; it does not replay a burst of old heartbeats. The current work item
skips missed sample slots. Late blink service computes phase from elapsed
time instead of adding delays and accumulating phase drift. Overload still
can miss a deadline, which is why timing is measured under simultaneous load.

## Fault policy and remaining evidence

- Cold start, bad input and UART timeout request dynamic braking and hazards.
  A self-test is now Pi-local: a single accepted press immediately latches UART
  command silence; the STM32 then detects timeout. Release debounce remains
  20 ms and the double-press window 400 ms. While latched, even stale/invalid UDP
  cannot trigger a Pi brake frame. Status RX/forwarding continues. See
  [the protocol](PROTOCOL.md#blinkers-self-test-and-steering).
- B1 retains the teammate's **latched enable-low/coast** stop until reset.
  B1 is not the checkoff's A-button dynamic-braking self-test.
- The STM32 timeout was changed from 80 to **60 ms** to implement the handout's
  three-missed-update policy at our 20 ms command cadence. Hardware deadline includes the next
  owner iteration and actual output change. The older 150 ms Part 2 and 100 ms
  checkoff bounds remain looser. For issue #2 the user confirmed timeout-based
  A self-test with this unchanged 60 ms threshold and checkoff's 100 ms target.
  This cannot meet the conflicting requirements-table 10 ms target; actual
  motor/lamp timing remains unmeasured.
- Pi UDP freshness remains 80 ms. It sends a brake frame then stops refreshing.
  Motor brake can occur before MCU link-error hazards: hazards follow up to
  another 60 ms later. Thus no <=100 ms *UDP-loss-to-hazards* claim is made;
  the handout's cable-loss test is Pi-to-STM32 UART loss. Ask the TA whether
  they additionally require the same hazard deadline for upstream UDP loss.
- Current telemetry is read-only. Unavailable/error/stale samples are
  `INT32_MIN` with clear validity bits, never fake measured zero. The 100 ms
  sample-age limit is a configurable initial telemetry policy, not a motor
  threshold. Part 3.5 uses nominal calibration and the user-selected 4.320 A
  upper-ADC-rail endpoint magnitude: -4320 mA motors/+4320 mA servo, with no
  symmetric current cap; physical sensor tests remain pending. See [current sensing](doc/CURRENT_SENSOR_HANDOFF.md).
- Servo boots with the tracked calibration and waits for healthy Pi commands
  and raw steering within -2000..2000. LIVE needs no USB heartbeat. Link/self-test
  recovery repeats the centered-wheel interlock; latched faults still block it.
  Optional manual calibration retains its 500 ms USB lease. Explicit OFF stays
  off until AUTO or manual ARM/LIVE. Physical recovery timing remains unmeasured.

Record measurements in [the blank worksheet](doc/PART4_MEASUREMENTS.csv).
Use [the test-point guide](doc/PART4_TIMING.md) for exact start/end markers.
