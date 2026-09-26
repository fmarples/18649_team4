# Lab 2 Part 2 — wheel to Pi to Nucleo

This folder contains the team's working Part 2 communication bring-up for a
Raspberry Pi 4, NUCLEO-F401RE, and Logitech G920 on Windows. It is separate
from the starter code at the repository root. **Use this folder's Pi bridge
and STM32 firmware together.** The root starter uses a different UART packet
format and checksum, so its Pi and STM32 halves cannot be mixed with these.

The team reports completing the ten hardware bring-up steps: wheel input
reached the STM32, a disconnected Pi-to-STM32 command wire caused a link
fault, the link recovered, and invalid frames were rejected. Exact hardware
latencies were not supplied with this commit. The code here is still a link
starter: it does not drive motors, a brake, the steering servo, or lamps.
Its current sensor values are marked unavailable and its state field is the
link state, not yet the vehicle zone state. See [PROTOCOL.md](PROTOCOL.md) for
the complete frame layout and timing policy.

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

## Hardware

Power down both boards before changing jumper wires. Pi GPIO is 3.3 V only.
Power the Pi from its own USB-C supply and the Nucleo from ST-LINK USB. Do not
connect their power rails.

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
   `lab2\tianyi\windows\start_wheel_proxy.cmd`. Enter the current Pi IPv4
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
reboot. To flash the Nucleo from an activated Zephyr environment, use this
folder as the app and a dedicated build directory:

```bat
set "TEAM_REPO=C:\path\to\18649_team4"
west build -b nucleo_f401re/stm32f401xe "%TEAM_REPO%\lab2\tianyi\stm32_zephyr" -d "%TEAM_REPO%\build\tianyi-part2"
west flash -d "%TEAM_REPO%\build\tianyi-part2"
```

Only flash when changing Nucleo firmware. The team already completed the
link bring-up; ordinary sessions can start the three programs above.

## Next integration work

Confirm the actual chassis component models and wiring before assigning new
Nucleo pins. Implement both encoders and motor velocity control, brake
override and verified dynamic braking, steering servo limits, blinkers and
hazards, and three calibrated current readings. Then replace the link-only
status and LED fail-safe with the vehicle zone state and safe physical outputs.
Measure timing on hardware for the handout's checkoff and document the final
schematic and task table.
