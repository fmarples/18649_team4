# Encoder-only bring-up — NUCLEO-F401RE

This is a separate Zephyr application, **not** the `stm32_zephyr/` Part 2 link app.
It does not link the motor driver, PWM, PID, steering, Pi command parser, or
watchdog. It reads four encoder inputs and prints telemetry over ST-LINK USB
serial (USART2, 115200 baud, 8-N-1) every 250 ms.

## Bench setup

- **Disconnect the 12 V feed to the L298N motor-power input.** Hand-turn wheels only. Make wiring changes with all supplies off; keep common signal ground.
- Nucleo uses the team's confirmed external E5V configuration. Keep the 12 V to 5 V converter branch connected, power it first, then connect ST-LINK USB for flashing/serial. Turning off the shared adapter also turns off the Nucleo. See [power setup](../../doc/HARDWARE.md#current-power-setup).
- Encoder VCC to 3V3 and GND to GND.
- Left A = PB3/D3; left B = PA8/D7.
- Right A = PB5/D4; right B = PA7/D11.
- L298N IN1–IN4 can remain disconnected for this test.
- Do not connect MCU PWM outputs to ENA/ENB while their jumpers are fitted.

See [the wiring plan](../../doc/STM32_PINOUT.md).

## What the firmware does

Each A/B input has an internal pull-up and an interrupt on both edges. The
quadrature state sequence determines the signed count: four counts per complete
A/B electrical cycle (x4 decoding). The ISR does not print, sleep, or allocate.
A spinlock protects count/state updates and telemetry snapshots.

A transition with both bits changing is ambiguous: it increments an invalid
transition counter and resynchronizes to the new state without inventing a
count. GPIO initialization/read errors are explicitly reported. Printing the
current A/B states is diagnostic; 250 ms telemetry cannot show every fast edge.

Positive is defined electrically as `00 -> 01 -> 11 -> 10 -> 00`. The hand-turn
tests and the user's confirmation of forward-first movement established:
**vehicle-forward decreases the left raw count and increases the right raw
count**. Future control code must negate the left count delta and retain the
right count delta before averaging velocities. This diagnostic intentionally
continues to print raw signed counts and does not calculate velocity. Subsequent
one-revolution hand measurements gave 1319 left and 1327 right absolute counts,
supporting **1320 counts/wheel revolution as the provisional x4 calibration**.
See [the calibration record](../../doc/ENCODER_SPEC.md) for the source conflict
and measurement limitations.

## Installed environment on the current Windows host

- Workspace: `C:\Users\13982\zephyrproject`
- Zephyr: `v4.3.0` (`3568e1b6d5cdd51a6b964a2a1d6d29200fea2056`)
- SDK: `C:\Users\13982\zephyr-sdk-0.17.4`, ARM toolchain only
- Python virtualenv: `C:\Users\13982\zephyrproject\.venv` (Python 3.12.10)
- Modules fetched at the Zephyr manifest revisions: `cmsis`, `cmsis_6`, `hal_stm32`
- Base Python requirements installed; other Zephyr modules/test dependencies
  have not been installed unless required by this bring-up.
- Nucleo currently enumerates as `COM4` and drive `D:` (`NOD_F401RE`). These can
  change when the board is reconnected.
- ST-LINK debug interface currently has Windows error 28 (missing driver).
  **Debug-probe flashing/debugging is not set up yet.** USB mass-storage flashing
  and the USB serial console are working and were used for these tests.
- An interrupted initial clone was preserved at
  `C:\Users\13982\zephyrproject\.west-interrupted`; the working clone is `zephyr/`.

## Rebuild

From PowerShell (the agent can run these commands):

```powershell
$ws = "$env:USERPROFILE\zephyrproject"
$repo = "C:\Users\13982\18649_team4"
$env:Path = "$ws\.venv\Scripts;" +
    [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
    [Environment]::GetEnvironmentVariable("Path", "User")
Set-Location "$ws\zephyr"
west build -b nucleo_f401re -d "$ws\build-encoder-test" "$repo\bringup\encoder_test" -o=-j4
```

Build output is outside the repository. Do not build/flash the Part 2 link app by
mistake; it replaces this encoder diagnostic. Initial toolchain configuration
can take several minutes on this host; use a command timeout of at least 300
seconds for a new build directory.

## Flash via the Nucleo USB drive

Verify the board drive letter and label first; do not blindly assume `D:` is
always the Nucleo. With motor power off, copy the built `zephyr.bin` to the
`NOD_F401RE` drive:

```powershell
Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,VolumeName
# Only after confirming D: is NOD_F401RE:
Copy-Item "$ws\build-encoder-test\zephyr\zephyr.bin" D:\encoder.bin
```

This programs/restarts the MCU, replacing the previous application. Check for
`FAIL.TXT` on the board drive and verify the serial telemetry after flashing;
successful file copying by itself does not prove the firmware is running.

## Hardware checks

The public test interface is the firmware's real USB serial telemetry. The
hardware check script requires the virtualenv's `pyserial` package and exclusive
access to the serial port (close other serial monitors first).

```powershell
# Commands shown for reproducibility; a human must rotate the wheel for motion tests.
& "$ws\.venv\Scripts\python.exe" "$repo\tests\check_encoder_serial.py" --port COM4 --seconds 5 --expect streaming
& "$ws\.venv\Scripts\python.exe" "$repo\tests\check_encoder_serial.py" --port COM4 --seconds 20 --expect left
& "$ws\.venv\Scripts\python.exe" "$repo\tests\check_encoder_serial.py" --port COM4 --seconds 20 --expect right
```

Wrap each command in an external execution timeout longer than the requested
capture (e.g. 30 seconds for a 20-second capture).

For each wheel check, start with both wheels still, then slowly turn **only the
selected wheel** forward for several seconds, pause, and turn it backward for
several seconds. Keep the other wheel still throughout. The check requires both
increasing and decreasing counts on the selected wheel and no movement on the
other channel. It rejects GPIO read errors and any increase in invalid
transition counters during capture. Record which count direction corresponds
to vehicle-forward separately.

Example telemetry format:

```text
ENC left=0 right=0 left_ab=11 right_ab=01 invalid_left=0 invalid_right=0 errors=0
```

## Verification so far

The initial streaming capture predates the team's confirmation of the corrected
external E5V power setup. Later hand-turn results are recorded below; they do not
independently verify supply voltage or jumper positions.

- Stock Zephyr blinky built and flashed; alternating `LED state: ON/OFF` messages
  were captured from the real board. Physical LED appearance was not separately
  confirmed by the user.
- RED: serial encoder check failed against blinky, as expected (no encoder frames).
- Encoder-only application built and flashed successfully.
- GREEN: 5-second serial check received 20 encoder frames, both counts zero,
  left A/B `11`, right A/B `01`, zero invalid transitions and zero read errors.
- Left-wheel hand-turn check passed (20 seconds, 79 frames): left counts moved
  in both directions (observed range -242 to 0), while the right count stayed 0.
- Right-wheel hand-turn check passed (20 seconds, 79 frames): right counts moved
  in both directions (observed range -66 to 169), while the left count stayed -36.
- Both hand-turn captures had zero invalid transitions and zero GPIO read errors.
- The user confirmed forward-first movement for both wheels: left forward is
  negative raw count; right forward is positive raw count. These signs are
  consistent with mirrored motor installation.
- One marked forward revolution per wheel measured left `-37 -> -1356`
  (delta `-1319`) and right `-67 -> 1260` (delta `+1327`). The other count stayed
  fixed in each capture, with zero invalid transitions and GPIO errors.
- These support a provisional **1320 counts/wheel revolution**, not the product
  page's predicted 3960. A multi-revolution repeat remains advisable.
- User reports wheel outside diameter **75 mm**, giving a geometric circumference
  of approximately **235.6 mm**. At provisional 1320 counts/rev this is about
  **0.1785 mm/count**, if linear velocity in m/s is used later.
- The separate [motor-test app](../motor_test/README.md) now reuses this x4
  decoder and pin mapping. Individual powered kicks verified channel identity
  and motor polarity; one simultaneous 5-second forward trial reported no invalid
  transitions or GPIO errors. This encoder-only image remains hand-turn-only.
- **Pending:** refined counts-per-revolution measurement, loaded rolling
  circumference if needed, independently verified high-speed accuracy, and
  closed-loop motor performance. Clean powered counts alone do not establish
  that every edge was captured.
