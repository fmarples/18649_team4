# Wheel GUI raw log and current chart

The user selected two buttons opening separate windows, rather than expanding
the driving window. The team launcher adds **Raw log** and **Current chart** to
the existing course GUI; the external course checkout is not modified.

## What the buttons do

- **Raw log:** timestamped events with checkbox filters for **Connection**,
  **Buttons**, **Steering**, **Pedals**, **Sensor status**, **Errors** and
  **Diagnostics**. Everything except Diagnostics is enabled by default.
  Link-state changes, telemetry loss/recovery, sensor availability
  and entering/leaving the current ceiling produce events once per transition.
  Normal current fluctuations and advancing counters do not produce log lines.
  The course proxy's repeated `No data` force-input poll message is suppressed
  before console/file output. Other stdout is diagnostic unless recognized as
  a connection event; stderr is an error. This is not the complete Pi terminal
  or ST-LINK text console.
- Filters affect only the view; all categories are saved. Pause freezes a
  snapshot, including while filters change. Clear clears only the view. Both
  leave event and sample recording active. Scrolling upward lets you inspect
  older lines without following new output. Continuous decoded status and raw
  frame bytes are saved separately in `.frames.jsonl`, not dumped into the view.
- **Current chart:** physically connected channels in signed amps over a
  rolling 30 seconds. The current default is left/A0 and servo/A3. The user
  confirmed right/A1 is disconnected and requested one startup error, with no
  right-channel legend, value, trace or contribution to axis scaling. This is
  explicit configuration, not an inference from a floating ADC value. Raw
  packet captures still preserve every field for diagnostics. Time is laptop
  reception time, not a physical timing measurement. Each channel has a distinct trace and numeric value. The axis
  includes negative readings, including unexpected values from an uncalibrated
  sensor. A +4.320 A reading is labeled `[ceiling]`, not treated as an exact
  overrange measurement.
- Missing packets and invalid sensor channels leave gaps, not invented zeros.
  After 500 ms without a fresh accepted frame, the GUI marks telemetry stale
  and replaces the current labels with unavailable. The old trace remains as
  history. Pause chart freezes a copy while acquisition and logging continue.
- Closing a log/chart window only hides it; its button reopens it. Closing the
  main proxy still stops its wheel stream as before. These new windows never
  send actuator commands or force feedback.

Memory is bounded to 3,000 history/log entries; the text view keeps at most
3,000 visible text lines. UDP reception uses Qt socket-readiness notifications,
not a polling loop. Log delivery uses signals. Timers only update chart/display
age and detect the freshness deadline. On-disk event and sample files retain
all recorded data for the session and can grow during long runs.

## Physical input events

The user selected separate Buttons, Steering and Pedals filters. The team
launcher observes the course proxy's existing outgoing DIJOYSTATE2 snapshots;
it does not poll the wheel SDK again or change packet bytes/destinations.
Events are recorded before sending, so a network send failure does not erase
the observed physical input. Connection/Stop button actions reset the baseline.

- All 128 SDK button slots log observed presses/releases. A/button 0 is labeled
  self-test, paddle 5 is left turn-signal request and paddle 4 is right request,
  matching the firmware mapping. Other buttons retain their index rather than
  guessed physical labels. A button already held at the first sample is marked
  `held on first sample`, not falsely reported as a new press.
- Wheel events show left/right, percent of center-to-lock travel, signed change
  in percentage points and raw input. These are not physical degrees; no wheel
  operating range has been independently verified for this logger.
- Accelerator and brake show released/pressed, percent travel, change in
  percentage points and raw input. Released is +32767/0%; fully pressed is
  -32768/100%. Unmapped slider/auxiliary axes retain their SDK names and raw
  changes instead of assuming a clutch/accessory mapping.
- D-pad/POV changes show direction or centered. Turn-signal requests describe
  physical paddle inputs, not acknowledgement that vehicle lamps changed.
- Identical samples do not repeat. Every observed raw change is retained,
  including small changes/jitter; there is no logging deadband. Events are
  limited by the course proxy's sampling cadence, so a press entirely between
  samples cannot be recovered. Nothing changes actuator policies.

To include a right sensor after it is physically connected, launch with
`--current-channels left right servo`. The current normal/one-click default
is `left servo`; the argument changes only visualization/event configuration,
not MCU sampling, status bytes or sensor calibration.

## Data path and deployment

```text
Nucleo status -> Pi UART -> Pi bridge -> laptop UDP 8002 -> log/chart
Laptop wheel commands -> Pi UDP 8000 -> Nucleo UART, unchanged
Course proxy force-feedback input: UDP 8001, not used for telemetry
```

The updated Pi bridge re-encodes each CRC-validated status byte-for-byte as one
UDP datagram. There is no firmware, UART-layout or CRC change. It learns the
laptop address only from an accepted advancing wheel packet, then keeps sending
status even if wheel commands stop. `--telemetry-host <laptop-ip>` explicitly
selects a destination when no wheel stream is running. Sending is nonblocking;
monitor/network errors are reported without stopping command forwarding.

Update **both** `pi/part2_bridge.py` and `pi/part2_protocol.py` on the Pi before
expecting data. Retain `pi/timing_gpio.py`, which the bridge already imports.
The existing deployment directory is `~/18649/part2`. Neither the GUI nor the
one-click session launcher deploys files automatically. Restart the bridge only
when ready to interrupt the vehicle command stream. Do not start a second
bridge to compete for UART or UDP 8000.

Start the normal GUI through the existing launcher:

```text
windows\start_wheel_proxy.cmd --pi <pi-ip>
```

Or use the separately documented [one-click session launcher](ONE_CLICK_START.md).
It starts/connects the GUI and retains these buttons. No MCU flash is needed.
Allow this Python application to receive UDP 8002 through the laptop firewall on
the intended network. The GUI binds the laptop interface selected by its route
to the Pi and accepts telemetry only from that Pi address. This is a lab-network
source check, not cryptographic authentication.

For a read-only session without the wheel SDK, launch:

```text
windows\start_wheel_proxy.cmd --monitor-only --pi <pi-ip>
```

In that case, use `--telemetry-host <laptop-ip>` on the Pi bridge because there
is no wheel stream from which to learn the destination. The monitor prints the
local address. The course Python environment supplies PyQt5; no charting package
is required. `--telemetry-port <port>` overrides 8002 on both programs. Both
CLIs reject ports 8000 and 8001 so telemetry cannot enter the force-input path.

If the GUI waits for data, first check that the updated Pi files are deployed,
that the bridge is running, and that a wheel packet has been accepted or an
explicit telemetry host was supplied. Then check the interface, firewall and
network reachability. Stale/invalid ADC data is distinct from absent network
telemetry; consult [Part 3.5](CURRENT_SENSOR_HANDOFF.md) for sensor calibration.

## Logs and crash reports

Every GUI session automatically creates:

- `logs/wheel-gui/<timestamp>-<pid>.log`: UTC timestamps, categorized events
  and proxy diagnostics. The Raw log window displays its full path.
- `logs/wheel-gui/<timestamp>-<pid>.frames.jsonl`: every accepted status frame,
  with reception timestamp, hexadecimal bytes and decoded `status` fields.
  These continuous samples are separate from event logs and checkbox filters.
- `logs/wheel-gui/<timestamp>-<pid>.crash.txt`: Python exception stack traces and
  faulthandler reports for supported native/interpreter fatal faults. It remains
  empty on a healthy run; no native minidump is configured.

`--log-dir <folder>` overrides the directory. Session logs are separate from
Pi CSV files and the one-click launcher's process logs. View pause/clear does
not delete or truncate files. A busy telemetry port produces an explicit startup
failure and persistent stack trace rather than pretending the chart is live.

## Verification

### Physical-input and disconnected-channel revision

Native Qt validation ran the real team launcher and external course window,
replacing only wheel hardware with synthetic DIJOYSTATE2 inputs and directing
all command packets to an ephemeral localhost receiver. The transmitted bytes
matched the original course serializer exactly. The walkthrough exercised
button/paddle/D-pad transitions, wheel/pedal amounts, unchanged samples,
separate filters, pause/resume, clear/reopen, and exactly one disconnected-right
startup error. No SDK initialization, force effect or vehicle command occurred.
Captured real MCU current frames were replayed through actual UDP. Visual
inspection confirmed the right legend/trace was absent and its floating values
did not affect axis scaling.

Evidence: `logs/wheel-gui/input-validation/`, including `input-events.png`,
`buttons-filter.png`, `chart-connected-only.png`, `host-tests.log`,
`protocol-tests.log` and `syntax.log`. Final suites passed **69 host tests and
10 protocol tests**. The user declined restarting the running session; it was
left untouched. The new behavior takes effect on the next GUI launch.

### Event-log revision

The user selected category checkboxes and event-only output, superseding the
original per-packet Raw log display. Separate windows and Pause/Clear behavior
remain. The native Qt walkthrough entered through the real monitor CLI, replayed
captured unavailable MCU statuses over localhost UDP and then sent synthetic
availability/ceiling transitions. It verified no per-sample log growth, checkbox
combinations, filter changes/clear/reopen, paused view with continuing sample
capture, and one stale event followed by recovery. Screenshots in
`logs/wheel-gui/event-validation/` were visually inspected. This did not send
hardware commands. The first walkthrough assertion assumed ERROR_TIMEOUT, but
the latest captured fixture was LINK_OK; the assertion now uses the recorded
state. The repeated walkthrough passed and released its ephemeral UDP socket.

Regression tests are `tests/test_telemetry_events.py` and
`tests/test_event_logging.py`. Continuous data no longer appears in the event
file; older session logs and the historical validation below retain that format.
The final combined suite passed **63 host tests and 10 protocol tests**, plus
syntax checks. Logs are `event-validation/host-tests.log`, `protocol-tests.log`
and `syntax.log` below `logs/wheel-gui/`.

After the sensor grounding correction and ADC firmware fix, a read-only check
of the running GUI's `.frames.jsonl` captured 20 advancing CRC-valid live MCU
statuses through the real Pi bridge. A0/A3 were no longer clipped; acquisition
validity was 7. A1 is physically unconnected, so its numeric values remain
unusable as current measurements. The event log recorded sensor changes and
had no `No data` spam. Evidence: `event-validation/live-gui-check.log`,
`live-gui-frames.jsonl` and `live-gui-events.log`. The running user session was
left untouched. See [ADC diagnosis](CURRENT_ADC_DIAGNOSIS.md) for the firmware
fix and remaining calibration work.

### Original GUI validation

The native Qt walkthrough used the real monitor CLI and real localhost UDP,
without the wheel SDK, UART access or actuator commands. It opened both windows,
paused and resumed them, cleared only the view, observed continuing file writes,
stopped packets to verify stale display, and reopened the dialogs. Recorded
negative-current values from the previous bench capture were replayed alongside
synthetic waveforms, missing samples and ceiling values. These are software
validation inputs, not new calibrated sensor measurements.

A second native Qt walkthrough attached the buttons to the actual course
`MyMainwindow`, replacing only its wheel SDK boundary and using ephemeral local
sockets. The Connect button and command timers were never activated. Screenshots
were visually checked for readable labels, signed axis range, gaps, stale state,
ceiling labeling and unclipped controls. All task-created processes/sockets were
closed; existing vehicle sessions were left alone.

Final verification: **58 host tests and 10 protocol tests passed**, with Python
syntax checks also passing. Run the suites with the course proxy's Python to
include the PyQt startup test. The full repository suite also needs `pyserial`
and the dependencies in `requirements-launcher.txt`; pyserial 3.5 was installed
in the existing course virtualenv for that run. The first full-suite attempt
failed only because pyserial was absent, recorded in `verify.crash.txt`.
Final results are in `host-tests.log`, `protocol-tests.log` and `syntax.log`.

Evidence is under `logs/wheel-gui/validation/`, including `wheel-buttons.png`,
`raw-log.png`, `chart-live.png`, `chart-ceiling.png`, `chart-stale.png`, and
`recorded-negative.png`. `tests/test_current_telemetry.py` covers protocol bytes,
CRC rejection, signed/zero/invalid readings, sequence wrap, duplicates, gaps,
reconnect and history bounds. Bridge tests cover forwarding, port isolation and
continued command handling when monitoring fails. `tests/test_gui_startup.py`
checks persistent failure reporting through the real CLI. No Pi deployment or
physical Pi-to-GUI telemetry test was performed during that software validation.

### Pi deployment, 2026-09-27

Deployed `part2_bridge.py`, `part2_protocol.py` and the required `timing_gpio.py`
to `/home/labuser/18649/part2` on `wheelpi`, with matching SHA-256 checks.
Restarted only the existing managed bridge service. Previous Python files and
its pre-restart CSV are preserved in
`/home/labuser/18649/part2/deployments/telemetry-20260927-235920/backup`.
Local deployment output is in `logs/wheel-gui/deploy-20260927-235920/deploy.log`.

At deployment, the service was active and receiving advancing MCU statuses.
the MCU reported `ERROR_TIMEOUT`, current validity mask 0 and all three currents
unavailable. The GUI log ended with `disconnecting` before deployment, so no
active wheel stream was available to teach the restarted bridge its telemetry
destination. No GUI was reopened or wheel connection initiated. Reopen/connect
the normal GUI to establish that destination, or use the documented explicit
telemetry host for read-only monitoring. Live reception was not verified at
this deployment step; the later live-path checks are recorded above. Unavailable
sensor readings must not be treated as measured zero.
