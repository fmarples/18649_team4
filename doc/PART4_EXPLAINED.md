# Part 4 explained using our actual car code

This explains main's implementation introduced by merge `3b04a43` and Part 4
commit `18da014`. The September 27 explanation does not change firmware.
Parts 3.3/3.4 were individually tested by Tianyi; combined hardware timing and
Part 3.5 remain unfinished. Use [the setup and test guide](../PART4_START_HERE.md)
for commands and [the task table](../PART4_TASK_TABLE.md) for checkoff.

## C versus Zephyr: we use both

**C is the language in which we write the instructions. Zephyr is the real-time
operating system and driver framework used by those instructions on the STM32.**
We did not replace C with Zephyr. The Part 3 motor and steering/blinker programs
were already C programs using Zephyr.

For example, converting a wheel value to a servo pulse in `servo_core.c` is C
arithmetic. Calling `pwm_set_dt()` asks a Zephyr driver to program the STM32's
PWM peripheral. `k_msgq_get()` waits for a message using Zephyr's kernel.

The STM32F401 has one CPU core. Threads take turns executing; their hardware
PWM peripherals continue generating pulses while another thread runs. A lower
priority thread can be interrupted when a higher priority one becomes ready.
That is preemption; it does not mean every task literally executes at once.

Example: the console is sending a diagnostic line when a brake command arrives.
The UART interrupt queues it; the control thread becomes ready, runs ahead of
the console and applies the brake decision. The console resumes later.
Interrupt-masked critical sections and locks can still delay this, so priority
alone is not proof of meeting a deadline. See [Zephyr scheduling](https://docs.zephyrproject.org/latest/kernel/services/scheduling/index.html).

A simple C loop could also be designed to meet deadlines, but you would manage
its scheduling yourself. This illustrative loop would be a bad design:

```c
/* Example of what our firmware DOES NOT do. */
while (1) {
    check_brake();
    turn_blinker_on();
    busy_wait_ms(500);
    turn_blinker_off();
    busy_wait_ms(500);
}
```

The next brake check could be nearly one second away. Our blinker checks the
time, writes the required light state and returns; it never waits half a second
inside the actuator loop. Zephyr still needs well-designed application code.

`app.overlay` describes hardware assignments such as servo PB9/TIM4 and motor
timers. `prj.conf` enables drivers/kernel features and sets the main priority.
The `.c` files implement behavior. These three pieces are built together.

## What changed when Part 3 was integrated

Before integration, the motor program and Tianyi's steering/blinker program
were separate firmware images on separate Nucleos. Flashing one image does not
also run another image. Integration combined their functions into one program
for the final motor Nucleo.

| Integration change | Why it matters |
| --- | --- |
| One command/state path and one actuator-owning thread | A brake or fault decision reaches motor, lights and LIVE steering consistently. Another actuator thread cannot later write an old motor command. |
| Preserved the motor/encoder/PID implementation | Keeps the existing 1320 counts/revolution, corrected forward signs, average encoder speed, pedal mapping and motor startup/running behavior. |
| Restored TIM2/PB10 for the right motor | The standalone steering setup had disabled resources that the motor setup needs. |
| Kept separate motor and servo timers | Left motor TIM3/PB4 and right motor TIM2/PB10 use 10 kHz; servo TIM4/PB9 uses 50 Hz. |
| PA5/D13 belongs only to front-right blinker | Old link-indicator writes must not fight the white blinker. Onboard LD2 shares PA5 and follows it. |
| Shared error/self-test policy | A enters self-test: dynamic motor brake, hazards and servo OFF. Link loss disables LIVE steering and requests brake/hazards. |
| Removed state-number conflicts | Motor fault remains 5; self-test is 6; actuator failure is 7. Pi and STM32 agree. |
| Tracked 1200/1600/2000 us calibration | The team's selected steering mapping can be loaded on the final board. It is specific to the tested servo/linkage. |
| Queued servo replies for background printing | The motor owner no longer waits to print a USB reply. |

Full throttle currently requests **300 RPM**, with targets below 23 RPM treated
as stopped. This is the documented current motor policy, superseding the earlier
110-RPM discussion; it is a requested target, not a promise the loaded car can
achieve it. Startup uses 60% for 200 ms, then the existing PID has 40..100% running
authority. We did not retune that controller during Part 4 preparation.

## What Part 4 added

- Defined and checked the application priority order: control 1, status 2,
  dedicated current-sampling workqueue 3, USB diagnostic console 4.
- Moved normal startup/runtime diagnostic printing out of the urgent owner.
  Whole-line synchronized printk is disabled. Initialization-failure prints
  still occur in startup thread context, after requesting a stop, not an ISR.
- Added a dedicated delayed-work current interface. Actual acquisition is
  intentionally unimplemented; ADC remains disabled and readings unavailable.
- Added optional Pi and STM32 timing markers so a scope can see event order.
- Made the STM32 command timeout 60 ms: three missed updates at our 20 ms
  command cadence. The handout also states 150 ms in Part 2 and 100 ms at
  checkoff; our shorter configured threshold is not a measured response time.
- Added logging, status-summary tooling, build/config checks, software tests,
  the actual task table, probe instructions and a blank results worksheet.

Software evidence: firmware build/configuration checks passed; 42 ARM/QEMU C
tests and 49 Python tests passed. Two additional host tests were skipped for
missing native GCC; their C contracts ran in QEMU. These do not prove hardware
timing. See [the exact evidence record](PART4_SOFTWARE_RESULTS.md).

## Answer 1: thread, work item, timer callback and ISR

| Tool | Plain meaning | Our actual use |
| --- | --- | --- |
| Thread | A task with its own execution context, stack and priority; can wait while other ready tasks run | Control/actuators, status transmission and USB diagnostics |
| Work item | A function submitted for a workqueue thread to execute; it inherits that queue's priority | Periodically call the current backend and publish a complete sample |
| Timer callback | A short alarm function executed when a kernel timer expires | Every 20 ms, give the semaphore that wakes the status thread |
| ISR | A short function run when hardware interrupts the CPU | Receive UART bytes, count encoder transitions, latch the B1 press |

The status timer callback does **not** build or transmit the whole frame. It
only signals `status_due`. The status thread does the longer operation.
Our current work item uses its **own priority-3 workqueue**, not the shared
system workqueue. A future blocking ADC conversion therefore does not occupy
the motor thread. The current backend still needs an appropriate bounded
implementation; merely putting work in a queue does not make it fast.
See Zephyr's [workqueue](https://docs.zephyrproject.org/latest/kernel/services/threads/workqueue.html)
and [timer](https://docs.zephyrproject.org/latest/kernel/services/timing/timers.html) documentation.

## Answer 2: periods and deadlines

**Period** means how often work repeats. **Deadline** means how soon the required
result must happen after its trigger. They are different. A 1-Hz blinker has a
one-second on/off cycle, but pressing its button must start it within 100 ms.

| Work | Period/trigger in our program | Priority/context | Deadline or target |
| --- | --- | --- | --- |
| Command receive | UART bytes; Pi forwards each new UDP state and refreshes at 20 ms | ISR then control 1 | Queue promptly; part of <=2 ms complete-command-to-motor-output path |
| Throttle/brake processing | On queued command; at most 1 ms queue wait when empty | Control 1 | <=2 ms motor-output response after complete command |
| Encoder feedback/PID | Nominal 20 ms sample interval; uses actual elapsed time | Control 1 | 20 ms feedback cadence; this is not permission to delay braking 20 ms |
| Blinker | Time phase checked each owner iteration; normal 500 ms ON/500 ms OFF | Control 1 | Response <=100 ms; 1 Hz +/-10%, 50% duty, paired edges <=1 ms apart |
| Hazards | 250 ms ON/250 ms OFF | Control 1 | 2 Hz; entry deadline depends on fault/self-test trigger |
| Steering | Serviced each owner iteration; PWM frame every 20 ms | Control 1 | Signal response <=50 ms |
| Status heartbeat | 20 ms kernel timer wakes status sender | Timer callback, thread 2 | Physical frame start-to-start interval 18..22 ms |
| Current sampling interface | Proposed 20 ms delayed work, skips missed slots | Dedicated queue thread 3 | No specific ADC deadline supplied; stale after 100 ms by initial telemetry policy |
| UART-loss watchdog | Checked every control iteration; expires at 60 ms since last valid command | Control 1 | Checkoff requires fail-safe <=100 ms |
| USB diagnostics | Replies polled between output bursts; diagnostics nominally every 250 ms | Thread 4 | Best effort |

These are configured periods and required targets, **not measured passes**.
Our receive marker is at completion of the 28-byte command; UART serialization
before that point is separate. At 115200 8N1, that frame takes about 2.43 ms.
Measure end-to-end propagation separately using the specified test points.

## Answer 3: what preempts what, and where are priorities set?

Among our application threads, smaller numbers mean higher priority:

```text
Hardware interrupts
        |
Control/actuator owner: 1
        |
Status transmitter:    2
        |
Current workqueue:    3
        |
USB diagnostics:      4
```

A ready priority-1 owner preempts threads 2, 3 and 4. Thread 2 can preempt 3/4;
thread 3 can preempt 4. Very short critical sections/lock ownership are relevant
exceptions to immediate execution. This diagram describes application work,
not every internal Zephyr thread or interrupt priority.

Exact places to show the TA:

- `stm32_zephyr/prj.conf:11`: `CONFIG_MAIN_THREAD_PRIORITY=1`.
- `stm32_zephyr/src/schedule.h:6`: status 2, current 3, console 4.
- `stm32_zephyr/src/main.c:183` and `:225`: create status/console threads with those priorities.
- `stm32_zephyr/src/current_sense.c:39`: start the dedicated current workqueue.
- `stm32_zephyr/src/main.c:284`: motor update; `:294` servo service; `:296` blinker service.

**Brake and blinkers do not preempt each other: they are functions within the
same priority-1 owner.** Motors are serviced first in each iteration; blinker
work only computes a phase and writes GPIOs, with no blinking delay loop.
If a new brake arrives during servo/blinker processing, its application waits
until the owner reaches command processing again. Those sections must stay
short enough for the 2-ms budget. Priorities protect the owner from slower
reporting/ADC/printing; scope measurement must prove its own worst-case latency.

## Answer 4: how does shared state avoid tearing?

Imagine a report reads NEW throttle but OLD brake because another context
updates the fields between reads. The resulting report combines two different
moments. Even when an individual 32-bit access is atomic, a group of accesses
is not automatically one coherent snapshot.

| Mechanism | Plain meaning | Use in this code |
| --- | --- | --- |
| `k_msgq` | Copy a complete item into a mailbox | Complete UART candidates and servo reply snapshots; USB RX uses a byte queue |
| `k_mutex` | Only one thread at a time may access the protected group of fields | `state_mutex` for command/report state; `current_mutex` for whole current samples |
| `k_spinlock` | Protect a very short operation shared with an ISR | Encoder counts and thread-side snapshots |
| Atomics | Update a small flag without a lost/partial read-modify-write | B1 stop latch and queue-overflow flags |
| Semaphore | A wake-up signal, not the measurement itself | Timer wakes status sender; startup releases console thread |

The status thread copies the needed values while holding a mutex, releases
it, then transmits. ADC waiting happens outside the current mutex. This avoids
holding shared state hostage while transmitting or waiting on a device.
Zephyr mutexes also support priority inheritance, but that does not remove the
need to keep critical sections short. See [mutex documentation](https://docs.zephyrproject.org/latest/kernel/services/synchronization/mutexes.html).

`volatile` tells the compiler about accesses; it does not lock several fields,
make a read-modify-write atomic or synchronize two threads. It is not our
replacement for these kernel primitives.

## Answer 5: does an ISR block, log or allocate?

Our application ISR paths do not sleep, wait on a mutex, print logs, allocate
heap memory or perform ADC acquisition. The queues and packet storage are
preallocated. Queue operations from the ISR use `K_NO_WAIT`; overflow records
an error rather than waiting for space.

- Pi UART ISR drains available bytes, recognizes framing, timestamps a complete
  candidate, toggles CMD_RX and queues it. CRC/range checks happen in the owner.
- Encoder ISR reads A/B and updates count/error fields under a short spinlock.
- B1 ISR sets an atomic stop latch. The owner applies the motor output policy.
- USB RX ISR queues bytes. Servo text parsing and replies occur outside it.
- Status timer callback only gives a semaphore.

This means no **blocking waits**, not zero execution time: FIFO draining,
copying and short driver/spinlock critical sections still consume time and
must be included in worst-case measurements.

## Testing everything together

Follow [PART4_START_HERE](../PART4_START_HERE.md) in order. It includes the
build/flash commands, one final board's wiring, three named operating windows,
expected outputs, individual checks followed by combined tests, fault recovery
and evidence collection. You can test 3.1-3.4 together before 3.5 is finished;
you cannot call all of Part 3 complete without the three real current readings.

Two current limitations to explain during checkoff:

1. Servo still needs its USB console heartbeat and explicit `arm`/`live` after
   a fault. Opening the console or loading calibration does not enable it.
2. Pi-to-STM UART loss and laptop-to-Pi UDP loss are different tests. UDP stale
   at 80 ms sends one brake command, then stops UART updates; error hazards
   can follow another 60 ms later. Do not claim <=100 ms UDP-loss-to-hazards.

The handout says these are guiding questions rather than a required separate
write-up. The task table is a deliverable, and the team should be able to
explain it and show real timing evidence at checkoff.
