# Steering without USB

## Decision

The user replaced the vehicle's explicit USB arm/live and 500 ms USB-heartbeat
requirement. They selected **require wheel centered first**, at boot and after
link/fault recovery, rather than enabling at an arbitrary wheel position.

Firmware embeds `config/servo_calibration.json`, currently 1200/1600/2000 us at
50 Hz. PWM starts disabled in WAIT_CENTER. A healthy Pi link, no inhibiting
fault and steering within inclusive -2000..2000 raw enable LIVE. LIVE follows
Pi commands without USB input or keepalives. Blinkers run concurrently.

Link loss, self-test and invalid steering disable PWM and require the centered
wheel interlock again. Motor/B1 and peripheral fault latches retain their
existing recovery/reset rules. Pedal braking does not disable steering.

Optional manual calibration keeps its 500 ms USB lease. Explicit OFF remains
off, including when the link recovers. SERVO AUTO re-enters WAIT_CENTER; existing
ARM/LIVE commands remain available for calibration. Opening or normally closing
the calibration console sends OFF. Physical USB disconnection alone does not
stop LIVE steering. Stored local console calibration is not automatically copied
to firmware: edit the tracked JSON and rebuild/flash to change boot calibration.

## Verification

- Regression first reproduced LIVE turning OFF after USB-heartbeat expiry.
- Native controller tests cover USB-independent LIVE, boot/link/center/fault
  gates, recovery, manual lease, explicit OFF and concurrent blinkers/self-cancel.
- Production `servo_bench_init/service` and the actual serial command parser run
  against narrow Zephyr UART/PWM boundary doubles. Tests verify embedded preset
  initialization, no-USB operation, OFF/AUTO, manual expiry, output errors and
  stop behavior. They do not simulate electrical behavior or physical motion.
- 45 host tests and 10 protocol tests passed.
- 8 servo and 7 combined-actuator Zephyr test contracts passed natively with
  assertion shims. This was not a Zephyr/QEMU scheduler run.
- NUCLEO-F401RE firmware build passed with Zephyr 4.3.0 and SDK 0.17.4.
  Flash 64,340 bytes; RAM 16,000 bytes.
- Firmware: `build/steering-auto/zephyr/zephyr.bin`.
  SHA-256: `5ddeafc5992a8c8cdda168164524020d3add0fd44ee09199823e18f95e88f5a7`.

**Flashed with user approval** to the separately confirmed COM4 Nucleo,
ST-LINK `066BFF505487525067171333`, mounted at D:. No ST-LINK FAIL.TXT appeared.
Startup telemetry reported WAIT_CENTER, pulse=0, the correct preset and zero
servo/lamp errors while the Pi bridge was stopped. After restarting the bridge,
STM reported LINK_OK with increasing sequences and zero rejected frames. Two
read-only SERVO STATUS replies three seconds apart reported LIVE and pulse=1596
at wheel raw -333. No USB keepalive was sent, and the diagnostic port was closed.
The user confirmed the car's steering follows the Logitech wheel while blinkers
also work. Physical cable-removal/recovery and timing checks remain unverified.

The approved image includes pre-existing, uncommitted current-sensor changes.
Those changes were not reverted or rewritten by the steering task. ADC telemetry
at rest reported roughly -8 A with valid bits set; these readings are not accepted
as calibrated physical currents. The user was informed; this separate issue was
not changed. No Pi protocol change was required for steering.

## Logs and remaining hardware check

Persistent build/test logs are in
`C:\Users\13982\18649_team4\logs\steering-autonomous\`:
`firmware-build.log`, `host-suite.log`, `protocol-suite.log`,
`changed-ztest-contracts.log` and `host-0.log` through `host-3.log`.
Deployment evidence is in `flash-console.log`, `flash-manifest.json` and
`live-no-keepalive.log`. The running Pi bridge is PID 2032 with logs
`/home/labuser/18649/part2/logs/steering-auto-20260927-230502.csv` and
`.console.log`. It is the existing Pi bridge; its old console text always labels
currents UNAVAILABLE, independently of the actual STM32 current telemetry.
The native tests preserve assertion failure output; the build runner preserves
Python tracebacks. USB diagnostics and Zephyr fatal traces can be captured with
`windows/servo_console.py --port <verified-port> --log <new-log-file>`, but opening
that calibration console requests OFF. Use a receive-only serial capture when
observing automatic startup. Pi bridge CSV/console logs remain under
`/home/labuser/18649/part2/logs/`.

After an authorized flash, with the linkage clear and normal power/wiring:

1. Verify no servo output without valid Pi commands.
2. With the wheel turned, connect the proxy; steering must remain disabled.
3. Center the wheel; confirm steering follows it and blinkers still work.
4. Without USB attached, repeat tracking and blinker operation for more than
   500 ms. Confirm actual motion, not just printed PWM values.
5. Interrupt the Pi link; output must disable. Restore it with the wheel turned;
   steering must wait until centered. Repeat for self-test recovery.
6. Check fault and PWM timing with the project's existing measurement procedure.

No physical timing, endpoint safety or combined power behavior is claimed by
these software tests.
