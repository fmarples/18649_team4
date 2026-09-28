# Intermittent motion investigation

Baseline: `147896c` (current sensing plus telemetry/input logging). The team
reported intermittent motor and servo movement after this integration. The
symptom has not yet been reproduced with synchronized input, UART, PWM and
power measurements; this patch is not proof that the physical issue is solved.

## Concrete software changes

- Windows previously wrote/flushed diagnostic files before forwarding some
  wheel commands, and on the same GUI thread that sends them. The Pi wrote and
  flushed CSV/console output inside its UART producer loop. Slow storage or
  stdout could therefore consume the 80 ms upstream freshness budget or cause
  the MCU's 60 ms watchdog to trip. Both now use bounded background diagnostic
  queues. Queue overload drops diagnostic records, never waits for storage;
  failures/drop counts are exposed. Command packets remain unmodified.
- The course GUI's two 50 ms timers are configured to 20 ms precise timers by
  the project wrapper. This matches the intended command cadence and provides
  more freshness margin. It is not a real-time guarantee on Windows or Wi-Fi.
- Firmware now acquires only selected sensors. The initial test image used
  mask 5: left motor/A0 and servo/A3; right/A1 remained unavailable. The user
  subsequently obtained the third ACS712-05B, so the new default is mask 7
  for installation of all three sensors. The earlier single-channel ADC
  sequence fix is retained, including averaging and whole-batch error handling.
- USB `DIAG` adds cumulative timeout/input/overflow counts, maximum accepted
  UART interarrival/owner-loop gaps and the commanded servo mode/pulse. These
  expose brief transitions that a 250 ms console snapshot could miss. They do
  not measure the physical PWM waveform. Counters reset at boot; intentional
  session stops can also increase timeout/gap values.

The patch preserves motor gains, 300 RPM maximum target, start/sustain duty
policy, braking, watchdogs, blinker/self-test logic, 1200/1600/2000 us steering
calibration and the team's centered-start automatic steering policy. Current
readings remain telemetry only, including the existing reporting ceiling.

## Build and regression evidence (2026-09-28)

- Zephyr v4.3.0 `3568e1b6d5c`, SDK 0.17.4, NUCLEO-F401RE. Isolated toolchain;
  the laptop's existing Zephyr 4.4.99 / SDK 1.0.1 installation was unchanged.
  This application overlay uses the 4.3 ADC binding. A newer Zephyr installation
  is not evidence of better actuator timing; keep kernel, modules and SDK
  versions consistent when reproducing the build.
- Matched modules: CMSIS `512cc7e895e8491696b61f7ba8066b4a182569b8`, CMSIS6
  `30a859f44ef8ab4dc8f84b03ed586fd16ccf9d74`, STM32 HAL
  `286dd285b5bb4fddafdfff27b5405264e5a61bfe`.
- Python discovery: 74 tests, 70 passed / 4 host-GCC-dependent tests skipped.
  Separate protocol suite: 10 passed. Blocked-file regressions exercise the
  actual Windows command wrapper and Pi bridge loop with fake transports.
- Zephyr QEMU integration: 46 passed, including production motor/servo cores
  and ADC backend doubles for masks 0, 5 and 7. This is not a hardware timing
  measurement. Host-only servo/driver boundary tests still require host GCC.
- Generated board configuration checks passed: separate motor/servo timers,
  GPIO assignments, ADC pins/reference, priorities and asynchronous printk.
- Main image: 64,868 bytes flash, 16,000 bytes RAM.
  Binary SHA-256: `bdd8517547fb6dcae7a35c233e2d4a552d0e6b818b2b892fdcad52a6ef14250e`.
- Flashed via Nucleo USB mass storage, ST-LINK `066BFF505487525067171333`.
  No FAIL.TXT appeared. A full old-flash dump was unavailable because SWD
  connection failed; baseline source remains in Git. Read-only USB telemetry
  after reset confirmed the new diagnostics, `WAITING`, `WAIT_CENTER`, zero
  servo pulse, target/duty/encoder counts zero, valid mask 5, and no ADC,
  servo, lamp or input errors. Owner-loop maximum gap was 2 ms during this
  idle observation. No wheel commands or USB actuator commands were sent.
- Subsequent supervised Wi-Fi live-link check: the user connected the Logitech
  wheel and reported no unexpected movement during the 60-second hands-off
  test. USB telemetry showed LIVE steering at 1600 us, target/counts zero,
  no timeouts/rejections/overflows, maximum accepted UART gap 22 ms and maximum
  owner-loop gap 3 ms. These software gap counters do not establish the 2 ms
  physical brake deadline. The SDK initially reported pedal axes as 0, keeping
  brake override active. After pedal initialization both released axes reported
  32767. The user also reported steady steering holds and three steady motor
  runs, with no observed unexpected motion in those checks.
- **Unresolved live finding:** six transient command timeouts accumulated near
  18:20:51 UTC (14:20:51 local), before the deliberate end-of-session stop.
  Maximum UART interarrival increased to 81 ms; owner-loop maximum stayed 3 ms,
  with no rejected frames, queue overflows or ADC errors. Captured status
  includes valid LINK_OK full-brake requests before timeout/recovery, and
  telemetry delivered in bursts. There were no Windows send-gap warnings in
  this interval. Network delivery/Pi scheduling and stale-input handling are
  under investigation; a physical twitch was not observed during this burst.
  The later timeout after clicking Stop is expected and is excluded. The
  intermittent-motion issue is **not yet considered fully resolved**.
- The first Pi CSV confirms that status reception on the Pi continued during
  the burst: maximum receive interval 21.4 ms over STM uptime 738000–744000 ms,
  while laptop receipt of the same status stream had gaps up to 144 ms. The Pi
  diagnostic queue reported zero drops. This separates healthy UART status
  reception from delays later in the return path, but does not distinguish
  network delay from laptop receive/event-loop delay by itself.
- Pi checks reported Wi-Fi power saving enabled, `throttled=0x0`, and
  `enable_uart=1`, with `/dev/serial0` resolving to `/dev/ttyS0`. The user then
  confirmed power saving disabled for a comparison. That run accumulated more
  timeouts and included Windows send gaps of 219–266 ms. However, the user
  subsequently reported that a teammate may have operated the controls while
  the user was away. Treat it as an **uncontrolled observation**, not a failed
  steady-input test or proof that power saving is the cause. No UART clock,
  watchdog, PID or sensor calibration settings were changed in response.
- Both comparison profiles built and passed generated board-configuration
  checks; neither was flashed. Quiet image SHA-256:
  `2a84e2d9dc4310fd7ed3e05e0a3f0f2fe0866d7ea35a28d33cb0c6137e1a1402`.
  No-acquisition image SHA-256:
  `d3eca6a16f2f10f88f74cdaa1ed0d8e8f0db3604d6909a93aecf6da054ffcb28`.

## Controlled comparisons if motion persists

Keep the wiring and command sequence the same and change one factor per run.
`diagnostics/quiet.conf` disables periodic USB text while retaining binary Pi
status and explicit console replies. `diagnostics/no_adc.conf` sets channel
mask 0, so no current acquisition starts and all currents are unavailable.
Pass either as `EXTRA_CONF_FILE` to a separate build directory. Neither changes
actuator policy; both are diagnostic configurations, not the normal lab image.

If the same constant command produces a physical twitch with stable commanded
servo pulse, target, encoders and error counters, inspect PWM and power/ground
at the hardware. If timeouts, UDP stale notices or sequence errors coincide,
inspect Windows/Pi scheduling and the network/UART path first. Current-sensor
insertion changes high-current wiring as well as software, so either can matter.
The software current ceiling does not limit the sensor's analog output voltage.
Nominal current conversion still needs per-sensor zero/reference calibration.

Detailed host-specific operating instructions and captured logs stay local,
outside this repository, per the team's documentation preference.

## Third current sensor follow-up

The tests above used the teammate's current-sensing baseline plus the stability
patch, not a rollback to the September 26 pre-sensor firmware. The new right
sensor preparation only enables its existing PA1/A1 acquisition and Windows
display. Nominal 5 A conversion constants and all actuator settings remain
the same. The original mask-5 binary and recordings are retained separately.
The mask-7 image built on the same isolated Zephyr 4.3.0 / SDK 0.17.4 stack:
64,844 bytes flash and 16,000 bytes RAM. Generated configuration checks passed,
including unchanged motor/servo timers, priorities and PA0/PA1/PB0 ADC mapping.
SHA-256: `553d8fafce74f9bdda8b69b2eb9efe6a321dac7355b2611e09be3c6ae969c592`.
Python regression: 74 tests, 70 passed and 4 host-GCC-dependent skips. An
offscreen Qt smoke check confirmed all three chart labels and the monitor's
three-channel default, without importing the wheel SDK or sending commands.
The image was subsequently flashed via the verified Nucleo mass-storage drive,
ST-LINK `066BFF505487525067171333`; no FAIL.TXT appeared. The user confirmed
raised wheels, stopped command programs and correct sensor voltages, without
providing exact meter readings. A 20-second read-only USB capture contained
77 complete current snapshots: valid mask 7 throughout, acquisition error 0,
sample age 2 ms. All captured states were WAITING, motor targets and encoder
counts were zero, and the requested servo pulse was zero. Nominal reported
currents were left 598–773 mA (mean 686.3), right 529–730 mA (mean 644.2), and
servo 614–845 mA (mean 717.2). These are uncalibrated readings, not established
load currents. The updated three-channel Windows GUI was opened disconnected.
This verifies idle acquisition only; a controlled live test is still pending.
