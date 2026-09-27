# Team 4 Lab 2

**Use `main`: start with [tomorrow's step-by-step Part 4 guide](PART4_START_HERE.md).**
The integrated code is now on main. The five completed/retired branches were
deleted after saving their tips as [archive tags](doc/BRANCH_ARCHIVE.md).
The [actual task table](PART4_TASK_TABLE.md), [probe-board instructions](doc/PART4_TIMING.md)
and [current-sensor handoff](doc/CURRENT_SENSOR_HANDOFF.md) are ready. The current
backend intentionally reports unavailable data; Part 3.5 and combined timing
tests are still pending. Tianyi reports 3.3 and 3.4 individually tested.
This branch combines main's motor/PID link with the blinkers, self-test and
opt-in steering console. It preserves the motor controller and fixes shared
pin/timer and status-code conflicts. The tracked steering preset is
[1200 / 1600 / 2000 us](config/servo_calibration.json). No combined hardware
verification has been completed. The branch-specific notes below describe
the original standalone benches, not this integrated image.

**Archived steering bench (`archive-lab2-tianyi-steering-2026-09-26`): [Part 3.3 instructions](doc/PART3_3_START_HERE.md).**
Adds disabled-at-boot, opt-in steering calibration on D14/PB9, a Windows console,
saved measured calibration, and wheel tracking to the corrected Part 3.4 build.
Safe linkage endpoints, actual power and waveform/timing validation remain
physical bench tasks. The section below describes the earlier blinker-only branch.

**Archived blinker bench (`archive-lab2-tianyi-blinkers-2026-09-26`):** the root STM32 app adds Part 3.4 blinkers
to the existing Part 2 UART link, for Tianyi's separate LED bench. Follow
[the complete start/test guide](doc/PART3_4_START_HERE.md). Motor/servo control
is still absent. The existing Pi bridge works unchanged; no UART format change
is required. See [Part 3.4 evidence](doc/PART3_4_RESULTS.md) for validation limits.
The historical Part 2 description below remains the baseline; its link-only
LED description is superseded on this branch by the guide above.

The repository-root `pi/` and `stm32_zephyr/` directories contain Tianyi's
Part 2 communication bring-up for a Raspberry Pi 4, NUCLEO-F401RE, and
Logitech G920 on Windows. The team agreed to use this root layout rather
than a lab/member subfolder. **Use this Pi bridge and STM32 firmware together.**
The old C bridge and full-control starter remain in Git history; their UART
format is incompatible with the current CRC-based protocol.

The team reports completing the ten hardware bring-up steps: wheel input
reached the STM32, a disconnected Pi-to-STM32 command wire caused a link
fault, the link recovered, and invalid frames were rejected. Exact hardware
latencies were not supplied with this commit. The code now connects the CRC link to encoder/PID motor control: a low-pedal
cutoff near 7.67%, active targets of 23..300 RPM, a 60% / 200 ms start kick,
40..100% running PWM, brake priority, B1 latch and link-loss braking.
**This integrated image is built and host-tested, not flashed or hardware-tested.**
The user deferred the Pi end-to-end run. Servo, lamps, current sensing and wheel
self-test remain pending. Current readings stay unavailable; status is link/motor
fault state, not full vehicle zone state. See [PROTOCOL.md](PROTOCOL.md).

## Contents

- `pi/part2_bridge.py` receives the course wheel proxy's UDP stream on port
  8000, sends UART commands, and reads STM32 status. `pi/part2_protocol.py`
  contains the packet encoder/decoder.
- `stm32_zephyr/` is a standalone Zephyr application for NUCLEO-F401RE.
- `windows/start_wheel_proxy.cmd` starts the separate course Windows proxy,
  prompting for the Pi's current IP address. Set `LOGITECH_WHEEL_REPO` to the
  course proxy repository folder if it is not alongside this team checkout.
- `windows/course_proxy_hwnd_fix.patch` is the small SDK wrapper fix used on
  Tianyi's Windows installation if the course proxy raises a `sip.voidptr`
  TypeError on Connect. Apply it in the **course proxy repository**, not here.
- `test_protocol.py` contains the host protocol/bridge tests.
- `bringup/encoder_test/` is the separate encoder diagnostic. Its decoder is
  reused through the motor-bench module in the integrated firmware. See its [instructions and results](bringup/encoder_test/README.md).
- [Encoder calibration](doc/ENCODER_SPEC.md) records the provisional 1320
  counts/wheel revolution at x4. [Simultaneous motor measurements](doc/MOTOR_CHARACTERIZATION.md)
  record 55% lowest tested startup and 40% lowest tested four-second holding duty
  after a 60% kick, with both motors together. See the
  [one-command sweep](bringup/motor_test/README.md#one-command-simultaneous-sweep)
  for guarded operation, logs and the unvalidated electrical/loaded limits.
  The separate bench app also has [continuous PID speed control](bringup/motor_test/README.md#continuous-pid-speed-control).
  One 45 RPM BOTH-wheel trial passed the provisional tolerance, averaging 44.1 RPM;
  broader tuning and load tests remain pending. The root app now reuses that PID.
- [Hardware BOM and power](doc/HARDWARE.md), [pin assignments](doc/STM32_PINOUT.md),
  and the [Lab 2 handout](doc/18-449_649%20Lab2%20-%20Sensors%20and%20Actuators%20v1_0.pdf)
  describe the hardware and requirements.
- [PART4_START_HERE.md](PART4_START_HERE.md) is the integration plan;
  [PART4_TASK_TABLE.md](PART4_TASK_TABLE.md) is the single scheduling proposal,
  replacing the older task-table template. Its proposed timings are not measurements.

## Hardware

Power down both boards before changing jumper wires. Pi GPIO is 3.3 V only.
Power the Pi from its own USB-C supply. The team's Nucleo uses external 5 V
from the HW-688 converter via E5V, with JP5 on E5V and JP1 open; apply external
power before connecting ST-LINK USB for flashing/debugging. Follow the
[power setup](doc/HARDWARE.md#current-power-setup). Do not connect the Pi and
Nucleo power rails. Keep motor power disconnected for link-only tests.

| Pi 4 physical header pin | Nucleo label | Signal |
| --- | --- | --- |
| 8, GPIO14/TX | D2, PA10/RX | Pi command to STM32 |
| 10, GPIO15/RX | D8, PA9/TX | STM32 status to Pi |
| 6, GND | GND | Common ground |

UART is 115200 baud, 8N1. The Nucleo ST-LINK USB serial console is separate
from this GPIO UART connection.

## Start an existing installation

1. Boot the Pi and connect the laptop and Pi to networks that can reach each
   other. The team registered the Pi on `CMU-DEVICE`; its IPv4 address can
   change. In the Pi SSH shell, run `nmcli device status` and
   `nmcli -g IP4.ADDRESS device show wlan0`. Drop the `/17` suffix when using
   the address with SSH, SCP, or the proxy. Direct Ethernet with the saved
   `lab-direct` profile is a recovery path if campus Wi-Fi blocks laptop-to-Pi
   traffic.
2. On the Pi, ensure both `pi/*.py` files are in `~/18649/part2`, then run:

   ```sh
   cd ~/18649/part2
   python3 part2_bridge.py --mode live --log "logs/live-$(date +%Y%m%d-%H%M%S).csv"
   ```

   `python3-serial` must already be installed and `/dev/serial0` enabled.
   Stop any old `wheel_monitor_readonly.py` process first; both use UDP 8000.
3. On Windows, connect and clamp the G920, plug in its pedals and power, and
   open G HUB. From this team repository, run
   `windows\start_wheel_proxy.cmd`. Enter the current Pi IPv4
   address, then click **connect** in the course proxy window with hands clear.
4. Open the Nucleo ST-LINK serial console from a Windows CMD with the Zephyr
   virtual environment active:

   ```bat
   python -m serial.tools.miniterm COM9 115200
   ```

   Substitute the current ST-LINK COM port if it changed. The Pi should print
   increasing status sequence numbers and the Nucleo should show `LINK_OK`
   with changing steering/throttle/brake values. `Ctrl+]` exits miniterm.

For a fresh Pi, enable hardware UART while disabling serial login in
`sudo raspi-config`, install `python3-serial`, add `labuser` to `dialout`, and
reboot. To build the Nucleo app from an activated Zephyr environment, run
from your Zephyr workspace and use the root `stm32_zephyr/` app directory:

```bat
set "TEAM_REPO=C:\path\to\18649_team4"
west build -b nucleo_f401re "%TEAM_REPO%\stm32_zephyr" -d "%TEAM_REPO%\build\part2"
west flash -d "%TEAM_REPO%\build\part2"
```

Flashing replaces the current bench image. The integrated app can drive motors
as soon as fresh Pi pedal commands arrive. Coordinate deployment before flashing.
For the raised-wheel motor bench, the user accepts possible reset/startup motion
and permits motor power to remain connected; see `AGENTS.md`.
`west flash` requires a working debug-probe driver; see the
[host setup and USB-drive alternative](bringup/encoder_test/README.md) if it is
unavailable, using this app's `build/part2/zephyr/zephyr.bin` rather than the
encoder binary. The team already completed link bring-up; ordinary sessions
can start the three programs above when the link firmware is installed.

## Host checks and logs

From the repository root:

```sh
python test_protocol.py
python -m unittest discover -s tests -p "test_*.py"
```

The second command checks the Windows launcher on Windows and skips it on
other systems. It uses a temporary stand-in entry point, not the real wheel GUI.
The encoder serial checker requires hardware and is run separately as described
in its README. Local verification of the root-layout change passed all seven
host tests and the Zephyr link-app build without flashing. Its test/build logs
are under `logs/root-layout/` on the verification host, excluded from Git.

The Pi command above writes status CSV files to `~/18649/part2/logs/`.
For persistent console output and Python exception traces, redirect that command's
stdout and stderr to a separate file in the same directory, for example
`> logs/bridge-console.log 2>&1`; create `logs/` first. No native crash dump is
configured. STM32 fatal output is on ST-LINK serial and must be captured by the
host; no on-board persistent crash storage is configured.

Pedal-mapping regression tests compile the real C mapper with a host GCC and
exercise every valid throttle value plus the cutoff boundary and brake priority.
Their logs are `logs/throttle-mapping/host-build.log` and `host-test.log`.
The integrated Nucleo binary is `build/pi-motor/zephyr/zephyr.bin`.
Integration build/test logs are in `logs/motor-integration/`, with
`verify.crash.txt` for preparation exceptions when produced. The bench image
was rebuilt as a compatibility check. Neither image was flashed for integration;
the physical Pi UART/motor end-to-end test remains deferred.

## Next integration work

Confirm the actual chassis component models and wiring before assigning new
Nucleo pins. Verify the integrated pedal/PID/brake/link-loss behavior on hardware.
Steering, blinkers/hazards and wheel-button self-test are combined on
`main`; verify them together with motors on the final board. Add
three calibrated current readings and a reviewed steering operating policy
that no longer depends on the development console. Complete the vehicle state.
Measure timing on hardware for the handout's checkoff and document the final
schematic and task table.
