# Lab 3 measurement firmware

Status: **Flashed and startup/traffic-validated on both Nucleos on October 19.** The user explicitly waived diagnostic backup; inconsistent readback attempts are not valid recovery images. ST-LINK debug drivers are installed. Selected task-pulse and Pi idle/stress measurements are recorded in [the timing ledger](../../doc/LAB3_TIMING_RESULTS.md). Full fault/queue behavior validation remains pending. See the dated deployment history below.

This variant drives GPIO/LED test points, not servo PWM or an H-bridge. N3 now runs the unchanged Lab 2 velocity PID calculation on synthetic encoder samples with observable output telemetry. N2 STEER now runs Lab 2's calibrated servo mapping on received synthetic commands and publishes the result without applying PWM; DRIVE remains a GPIO stand-in. See the latest steering measurement revision below for the workload and current deployed images. The user requested measurements only, not a task graph or final checkoff implementation.

## Measurement changes

- STEER/DRIVE now have a separate queued worker; their body time is no longer nested in RX dispatch.
- BLINK_F/R run in a separate event-driven worker instead of the main loop's 2 ms polling. Error-hazard edges retain an absolute 500 ms deadline across intervening events.
- Workers wait until GPIO, both CAN devices, all seven filters per controller and the watchdog initialize successfully.
- HB_MON runs phase-locked every 20 ms, matching the template, rather than sleeping 5 ms after each iteration. HB_TX is 20 ms, PID 10 ms and FORCE_TX 50 ms.
- CAN transmission uses a completion callback. `can_send` returns after queueing/loading rather than waiting for a wire ACK. Hardware TX-slot waiting remains bounded by the existing 2 ms timeout. Rejected submissions and completion failures are counted separately.
- The optional Part 4 relay is disabled by default. `CONFIG_LAB3_RELAY=y` enables it on N2, requiring new measurements.
- `CONFIG_WATCHDOG` replaces the obsolete `CONFIG_WDT`. The unsupported manual-recovery task is excluded in this MCP2515 build; automatic bus-off recovery remains a hardware verification item.
- Named cycle-counter records retain raw cycles, upward-rounded microsecond maxima and counts. Diagnostics print every five seconds, not every 250 ms.

These changes alter the workload. Do not mix these measurements with old starter timings or the Part 0 diagnostic scope captures.

## Console and GPIO interfaces

After the online banner, `timing probe NAME` selects one task's elapsed-body pulse on **PC8**. `timing probe off` disables the pulse. No reflash is needed to switch tasks. PC8/CN10-2 was scope-verified on the board ending 124020/COM6, now logical N2 after the role swap; the scope has since moved to Pi GPIO markers; keep it isolated from actuators. Bus-specific `rx_dispatch_a/b` selection is available. `timing tx off|on` pauses/restores application submissions for isolated receive tests; wait for queued frames to finish. Existing test points remain unchanged.

Available body names are `rx_dispatch`, `rx_dispatch_a`, `rx_dispatch_b`, `steer` on N2 or `drive` on N3, `hb_mon`, `hb_tx`, `test_btn`, `blink`, plus `force_tx` on N2 and `pid` on N3. `relay` is available only in the optional relay build. Discard acquisitions during a selection change.

Example record format, not a hardware result:

```text
OBS_TASK zone=N2 uptime_ms=5000 name=hb_tx max_cycles=85 max_us=2 count=250
```

Parse current logs using `measurements/parse_stm32_console.py LOG --tasks --out OUT.csv`. Omit `--tasks` only for archived `OBS_MAX_US` logs. A malformed named record fails parsing instead of silently dropping a sample. **Count zero means unmeasured or absent**, not a zero execution-time bound.

| Counter | Measurement boundary |
|---|---|
| `steer` / `drive`, `hb_mon`, `hb_tx`, `force_tx`, `pid`, `blink` | Body entry to body exit, excluding the preceding queue/semaphore wait or periodic sleep |
| `test_btn` | Accepted press handling after the 2 ms debounce; excludes ISR, wake-up, debounce and ignored edges |
| `relay` | Each dequeued candidate, including the eligibility check and any forwarded send call |
| `rx_callback_a/b` | Application callback only, after the driver's SPI read |
| `rx_queue_a/b` | Timestamp just before enqueue to dispatch dequeue; includes callback tail, queue operations, scheduling and backlog |
| `rx_dispatch_a/b` | Application dispatch per bus, including validation, deduplication, state updates, event/queue submissions and the aggregate timing-record update |
| `rx_dispatch` | Aggregate application dispatch body, ending before its timing-record update |
| `rx_callback_to_end_a/b` | Same-frame application callback entry to dispatch completion, including post-body bookkeeping; excludes earlier ISR/driver SPI work |
| `control_queue` | Timestamp before control enqueue to worker dequeue |
| `can_tx` | One `can_send` call plus its marker and rejection accounting; includes TX-slot/mutex/SPI waits, but not wire completion |
| `overhead` | 1000 back-to-back clock-start/end observations at boot; not the cost of all instrumentation |

The counters measure **elapsed time, not pure CPU execution**. Preemption, nested work and resource waits remain inside a timed body. The PC8 pulse includes the timing accumulator's end bookkeeping, whereas the reported cycle interval ends before that bookkeeping. Keep the raw readings and measurement overhead; do not silently subtract the minimum. Counts/maxima are lifetime statistics until reset. A 32-bit cycle interval must be shorter than one wrap, approximately 51 seconds at 84 MHz.

Do not add overlapping measurements: `can_tx` is nested in HB_TX/FORCE_TX/button/relay bodies, and RX queue intervals overlap part of the callback. These counters do not include the MCP2515 ISR and driver work preceding the application callback, full release-to-completion response, or a proved mutex-blocking maximum.

## Scheduling relevant to interpretation

The installed MCP2515 driver creates two **cooperative** workers with `K_PRIO_COOP(2)`, which is -14 with the current 16 cooperative priority levels. It does not create preemptible priority-2 workers. The application priorities are dispatch 1, BLINK 2, STEER/DRIVE 3, TEST_BTN 4, PID 5, HB_MON 6, HB_TX 7, FORCE_TX 8 and diagnostics 10. Optional RELAY shares priority 2 with BLINK. Lower numbers have higher priority.

Account for the two receive streams, cooperative-driver execution, SPI sharing, shared-state mutexes, fault/state-change wakes and the error-hazard timer. A seven-message catalog does not mean a single 20 ms receive activation. No schedulability verdict is claimed here.

## Remaining measurement limits

- The demo's deduplication/reboot handling, stale-input policy, fault-rate enforcement and error recovery have not been repaired or validated as part of this work.
- The handout's heartbeat-loss error chain differs from this starter's continuing ERROR heartbeats and FAULT messages. Do not report it as the same measured chain.
- DRIVE remains a GPIO stand-in. PID runs the real Lab 2 calculation with synthetic inputs; STEER runs the calibrated Lab 2 mapping. Physical sensor acquisition, PWM output and the full autonomous steering policy are excluded.
- Isolated CAN A INT-to-dispatch-completion was measured at 404 us. Loaded/per-bus coverage remains separate; the earlier diagnostic 336 us INT-low interval is not the application receive result.
- Pi software-only idle/stress trials now have 65 s of synthetic wheel-format UDP input each at 20 ms, with maximum/p99 recorded in `doc/LAB3_CAN_BRINGUP.md` and raw artifacts under `logs/lab3-can/20261019-061302-pi-latency/` at the repository root. Later paired-GPIO idle/stress captures are also recorded in the timing ledger. The earlier trials did not enable GPIO tracing; actual wheel-proxy integration remains pending.
- Resolve the physical A/B label mismatch in `doc/LAB3_CAN_BRINGUP.md` before per-bus or relay comparisons.

## Verification and retained artifacts

Verification on 2026-10-19: both builds passed; four host measurement tests and nine existing protocol/wheel tests passed. N2 uses 97,744 bytes flash; N3 uses 97,760 bytes. Each uses 32,448 bytes RAM. Build logs are `logs/lab3-can/20261019-041704-build-n2.log` and `20261019-041704-build-n3.log`. Test logs are `measurement-host-tests.log` and `measurement-protocol-tests.log` in the same directory. Read-only review caught a control-queue purge wake-up, a missing CRC-error blinker notification and a relative hazard-timer restart; these were corrected and both targets rebuilt. Those worker scenarios still need target scheduling tests.

The retained `logs/lab3-can/20261019-042029-measurement-build/` directory contains both binaries/ELFs, generated configurations/devicetrees, application sources and a SHA-256 manifest. **This archive is new measurement firmware, not a backup of the flashed diagnostic.** N2 binary SHA-256: `772b26bb83f5ab9a7364f54f19a6b1670ba4775357983bb7e2b3200ae10bac17`; N3: `ba26e320dfbcdc510cd796710557383889da7f85a2c7a16ef59d28ff0331a59d`.

Initial discovery found no probes. ST's signed debug driver was subsequently installed, and pyOCD now sees both probes. Running-target attach failed; under-reset reads were inconsistent and rejected. No verified diagnostic backup exists, and the user explicitly waived that prerequisite. See `stlink-driver-signatures.json`, `stlink-signed-driver-install.log` and `stlink-probes-after.log` under `logs/lab3-can/`.

Host tests exercise the real C timing accumulator and probe command through clock/GPIO/shell test adapters, plus the actual parser CLI. They verify upward rounding, rollover, maximum/count retention, available task selection, pre-init rejection, probe-off behavior and malformed-log rejection. They do not emulate RTOS scheduling or prove the target GPIO/electrical behavior. Target build success is not a runtime test.

Build/measurement logs and scope photos are retained under repository-local `logs/lab3-can/`, which is Git-ignored. The Windows absolute location is `C:\Users\13982\18649_team4\logs\lab3-can\`. Capture the complete serial stream during target runs, including Zephyr fault reports, in timestamped `*-COM4.log` / `*-COM6.log` files there. `CONFIG_FAULT_DUMP=2` enables register/context fault diagnostics. The logging coredump backend also emits the faulting thread's context and stack; retain those lines and the matching ELF for offline stack backtraces. Use Zephyr's `scripts/coredump/coredump_serial_log_parser.py` and `coredump_gdbserver.py` to decode a captured dump. Coredump delivery is build-configured but not fault-injection-tested; the watchdog may interrupt an unusually long dump. No MCU crash dump was observed; subsequent timing captures are recorded in the bring-up history.

Build artifacts on this host are `C:\Users\13982\zephyrproject\build-lab3-measurement-n2\zephyr\` and the corresponding `-n3` directory. Source hash/diff, binary hash, generated `.config`, `zephyr.dts`, selected task, clock settings, logging and load conditions must accompany actual measurement runs.


## October 19 measurement-firmware deployment

The user explicitly waived diagnostic backup. Wiring, the requested 1 MHz SPI
clock and measurement-only scope remain unchanged. No valid diagnostic recovery
image was obtained; attempted readbacks must not be used for restoration.

Both measurement images were deployed through serial-matched ST-LINK storage:
N2 `066BFF505487525067171333` (COM4/D:) and
N3 `066BFF485270535067124020` (COM6/E:). Ports were rediscovered before use.
The first image restarted repeatedly because the STM32 watchdog driver installed
its boot timeout before the app installed its own (`-ENOMEM`). The corrected
configuration uses `CONFIG_WDT_DISABLE_AT_BOOT=y`; main still installs and feeds
the application's watchdog. Both rebuilt images reached their correct online
banner, each emitted 54 OBS_TASK records in the startup capture, and reported
zero TX rejects/completion failures in those captures. No FAIL.TXT was present.

The deployed archive is `logs/lab3-can/20261019-043636-measurement-build/`,
including sources, binaries, matching ELFs, configurations and hashes. The earlier
042029 archive contains the watchdog-conflicting image and is not the deployed
version. N2 SHA-256:
`6f8d24cef7e664fb3a214caae37253bfb400531f1aa24cbca569ec3ee15a80e6`;
N3: `702e6f5d92b0a484c047d772620480d745116f0dcf215c7c1053f97d39f821a8`.

A three-second Pi capture received 150 frames each of IDs 0x101 and 0x102,
and 60 frames of 0x300, on **each** bus. COM6 accepted `timing probe hb_tx`
and `timing probe off`; selection was left off. PC8/CN10-2 is not yet physically
probed. Firmware now transmits automatically; the old diagnostic's TX-off state
and `lab3 stop` commands no longer apply. No Pi bridge was started; bounded
candump exited. Physical timing, fault-injection, actual actuator workloads and
Pi idle/stress latency remain unmeasured.

Persistent evidence (Git-ignored):
- `logs/lab3-can/20261019-043803-measurement-flash-n2-COM4.log`
- `logs/lab3-can/20261019-043803-measurement-flash-n3-COM6.log`
- `logs/lab3-can/measurement-deployment-latest.json`
- `logs/lab3-can/measurement-firmware-traffic.log`
- `logs/lab3-can/measurement-probe-command.log`
- `logs/lab3-can/measurement-host-tests-after-flash.log`

The complete serial logs are also the crash-report location; retain any logged
coredump with the matching archived ELF. No crash dump was observed in the
successful startup captures, and coredump behavior remains untested.


## Built-in B1 measurement firmware

The user replaced the external PA8 test-button plan with the Nucleo built-in
blue B1 button. The baseline overlay now maps TEST_BTN to PC13 active-low,
matching the installed board's sw0 definition. The CAN/probe wiring, SPI clock
request, watchdog configuration and measurement task bodies remain unchanged.

Both N2 and N3 were rebuilt and flashed using freshly discovered serial-matched
ST-LINK drives. Correct online banners and timing records passed. N3 accepted
`timing probe test_btn` and is selected for the physical B1-press capture. Physical
press verification is pending. No external PA8 button is needed. The TEST_BTN
pulse starts after debounce and covers processing a press, including fault-frame
submission on both buses; it does not pulse continuously while unpressed.

Current deployed archive: `logs/lab3-can/20261019-051047-b1-measurement-build/`.
The earlier 043636 archive precedes this button mapping change. Checksums:
- N2 066BFF505487525067171333: `7d3be6a78ce5ef22e516c3efb69b790cba11e7bd67e4c3d2466325411e4b213b`; boot log `logs/lab3-can/20261019-051047-b1-flash-n2-COM4.log`.
- N3 066BFF485270535067124020: `5861456bfef9aff21fdc2fdbaca95ff41f1c2e2867e32219758bb2993c19bfa8`; boot log `logs/lab3-can/20261019-051047-b1-flash-n3-COM6.log`.

`tests/check_lab3_button.py` checks the generated devicetree against the board's
B1 GPIO controller, pin and active polarity. It failed against the original PA8
mapping and passed both rebuilt images. Use trusted local `zephyr/edt.pickle`
artifacts and Zephyr's python-devicetree module on PYTHONPATH.

Persistent deployment summary: `logs/lab3-can/b1-deployment-latest.json`.
Full serial logs also retain any crash reports; matching ELFs are in the archive.
No crash report was observed in these startup captures.


## PID and CAN measurement revision, October 19

The user changed the measurement order: stay on N3, repair the earlier workload
and boundary gaps, then remeasure before moving to N2. They chose reuse of the
Lab 2 PID calculation with synthetic feedback. The 1 MHz SPI request, B1/PC13,
PC8/CH1 and PB6/CH2 wiring, and non-actuating behavior remain unchanged.

### PID workload

N3 now links the unchanged `bringup/motor_test/src/velocity_control.c` directly,
not a copied approximation. No motor driver, encoder driver or PWM output is
linked. The 10 ms worker supplies one synthetic 20 ms encoder sample per
activation, so the Lab 2 core's 20 ms minimum interval does not skip alternate
computations. This is independent synthetic time, not a live 10 ms control loop.
Three 100-sample phases use targets 150/300/23 RPM and encoder increments
44/88/132 per 20 ms, equivalent to 100/200/300 RPM. The third phase starts a
fresh controller to exercise the lower clamp. The 300-sample cycle repeats with
bounded counts; outputs remain observable through `PID_WORKLOAD` telemetry.
The pulse includes fixture preparation, real PID calculation, result conversion
and marker work; publishing/printing telemetry happens afterward. N3 enables
FPU/FPU_SHARING like Lab 2. STEER and DRIVE remain GPIO stand-ins.

Host tests verify independently worked initial outputs 66.35 and 66.70 percent,
changing outputs, both duty clamps and repeated fixture cycles. Target startup
records show duties 66350, 40000, 100000 and 86649 milli-percent with status=0.
Disassembly confirms pid_thread calls lab3_pid_measurement_step, which calls
velocity_update and velocity_retarget; calculation survives optimization.

### Heartbeat and receive boundaries

- Existing HB_TX elapsed pulses are retained. `OBS_THREAD name=hb_tx` separately
  reports per-activation thread-accounted execution, using 64-bit runtime deltas.
  It excludes switched-out time but can include IRQ time charged to the thread;
  it also includes measurement-call overhead around the GPIO body. It is not
  the earlier elapsed counter under another name. Runtime stats are enabled on
  both nodes, adding scheduler instrumentation overhead.
- `timing probe rx_dispatch_a` and `rx_dispatch_b` restrict the GPIO marker to
  one bus without changing processing. Aggregate `rx_dispatch` still works.
- `rx_callback_to_end_a/b` measure each frame's own callback-entry timestamp to
  dispatch completion, including post-body bookkeeping. These exclude earlier
  GPIO ISR and SPI/driver receive work; they are not full CAN_RX time.
- `timing tx off|on` gates new application CAN submissions. Already submitted
  frames can finish; callers retain their periodic tasks and state processing.
  Default is on. Both boards acknowledged off, a three-second Pi capture was
  quiet, then both acknowledged on. Normal automatic traffic is restored.
- For the later full receive elapsed measurement, pause TX on BOTH boards,
  verify the bus is quiet, then inject isolated valid frames on Pi can1, which
  reaches N3 CAN A. With CH2 moved to PA10 INT and CH1 selected rx_dispatch_a,
  measure INT falling to the matching dispatch pulse's end. This physical
  measurement is pending. Avoid pairing unrelated TX/error interrupts or a
  batch of multiple received frames with a single dispatch.

### Deployment and pending capture

Archive: `logs/lab3-can/20261019-053026-pid-rx-measurement-build/`. It includes both images/ELFs, generated
configurations/devicetrees, app sources, the externally linked Lab 2 source and
SHA-256 manifest. Both images passed startup/timing validation; the B1 generated
configuration test still passes. N3 accepted rx_dispatch_a and was finally
selected to **pid**. Normal TX is on; no Pi stimulus or test server is running.
The physical probes have NOT moved. The next step is the revised PID scope
capture on N3, followed by revised heartbeat and isolated receive measurements.

Earlier scope results remain associated with their earlier firmware. The 11 us
PID-demo result belongs to the removed empty workload, not the new calculation.
Startup software counters reported PID max 16 us, heartbeat elapsed max 817 us
at the sampled records and heartbeat thread-accounted max up to 646 us; these
are serial startup observations, not new scope results.

Evidence:
- `logs/lab3-can/measurement-revision-deployment.json`
- `logs/lab3-can/measurement-revision-host-tests.log` (five tests passed)
- `logs/lab3-can/revised-n3-disassembly.log`
- timestamped `*-revision-build-*`, `*-revision-flash-*`, `*-tx-gate-*` and
  `*-tx-off-quiet.log` under `logs/lab3-can/`.
Serial logs retain crash reports; matching ELFs are in this archive. No crash
report was observed during the successful startup captures.

N2 binary SHA-256: `e9f3c74364add5679d2872d1ddddd32f91428b08bb45505d5818d77ad4887f1e`.

N3 binary SHA-256: `daa66c9893b68ede9ceec379da4bcee0ea33f58a0e647ee17c133178cf6b28b5`.


## Lab 2 steering calculation measurement revision

The user chose to replace N2's GPIO-only STEER body with the existing Lab 2
steering calculation before measuring it. The application links unchanged
`stm32_zephyr/src/servo_core.c`; its adapter calls `servo_map` using the tracked
`config/servo_calibration.json` endpoints 1200/1600/2000 us. CMake generates the
same calibration header template as Lab 2 and rejects invalid endpoints. This
measures calibrated mapping, not servo PWM output or the complete autonomous
steering policy. The pulse ends before publishing output telemetry. No servo
hardware driver or PWM application code is linked into this workload.

Host tests check all five selected positions, exact endpoints/midpoints and
monotonicity across the complete int16 command range. All six measurement tests
passed. Both rebuilt images passed B1 configuration checks and boot validation,
retaining the swapped roles: N2 ending124020/COM6, N3 ending171333/COM4.
No physical wiring moved: CH1 PC8 and CH2 PA10 INT on the now-N2 board.

Current build archive: `logs/lab3-can/20261019-060412-steering-measurement-build/`. It includes both binaries/ELFs,
configs/devicetrees, generated N2 calibration header, app sources and externally
linked Lab 2 PID/servo sources and calibration, with SHA-256 manifest. Earlier
measurement results retain their original firmware archive labels.

N2 binary SHA-256 `fb807214eb41b3c5546cafa43127b0bedfbef4a34dd782d4a04c319b537724a6`; boot evidence `logs/lab3-can/20261019-060412-steering-flash-n2-COM6.log`.

N3 binary SHA-256 `853b7dfe53f0f264bc2f8ab1e91ed97d14dbc7edd5dd44e3dd9959b7c3d374c5`; boot evidence `logs/lab3-can/20261019-060412-steering-flash-n3-COM4.log`.


N2 accepted `timing probe steer`. Both boards have normal application TX on.
A user-authorized continuous Pi stimulus is running on both CAN interfaces,
period 20 ms, steering positions 0/-32768/-16384/16384/32767 held for 25 frames
each, throttle=0 and brake=100. No N1 heartbeat or fault-clear is injected.
The mapping workload consumes accepted commands despite the surrounding demo's
error state; it only reports results and never applies them to a servo.

Target evidence `logs/lab3-can/20261019-060538-steering-live-verification.log`
shows STEER sample count increasing 899 to 1160, pulse values 1600 and 1200 us,
minimum 1200 and maximum 2000 us, hardware_output=0, and no TX rejects/failures.
Software timing maximum in that check was 7 us; scope result is pending.
`logs/lab3-can/revised-steering-disassembly.log` confirms control_thread calls
lab3_steering_pulse, which calls the original servo_map; work survives optimization.

Continuous sender PID 2227 is intentionally left running, per the
user's instruction to keep measurement traffic running unless stopping is
necessary. Ownership/start/stop tools and state are in
`logs/lab3-can/continuous-steer/`. Remote persistent stdout/crash-trace log:
`/home/labuser/.local/state/team4-lab3/steering-e456788e41304c8987cc44cba780c834/stream.log`. Stop only for a necessary test transition or user request;
do not end this capture after a fixed time. The older isolated-RX sender remains
stopped. Next: obtain the STEER scope maximum/mean/count with CH1 positive width.
