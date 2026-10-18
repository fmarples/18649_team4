# Lab 3 Dual-CAN Starter — N1 Pi + N2/N3 STM32

This is a **separate Lab 3 demo application** layered beside the uploaded Lab 2 project. It does not overwrite or remove the Lab 2 code. It keeps the existing 276-byte UDP wheel-proxy input format and replaces UART with classic CAN frames over `can0` and `can1`.

The STM32 builds are deliberately **demo-only**: LEDs, GPIO test points, and printed control values. They do not initialize the steering servo or motor/H-bridge modules. Do not treat the output GPIO markers as actuator drivers.

## Files and responsibilities

### Raspberry Pi (`pi/`)

- `cockpit_bridge.py` — N1 main loop: reads wheel UDP on port 8000, transmits CTRL on each valid update, sends a safe demo brake request when UDP goes stale, sends HB_N1 every 20 ms, drives BLINK state/phase, receives heartbeats/FORCE from both CAN interfaces, and writes event/timing CSV.
- `can_protocol.py` — message IDs, fixed 8-byte payload serialization, sequence nibbles, CRC, decode/validation.
- `wheel_input.py` — pure decoder for the existing 276-byte Lab 2 UDP packet and normalized pedal percentages.
- `timing_gpio.py` — optional libgpiod v2 probes: UDP_RX BCM17, CMD_TX BCM27, CAN_TX_A BCM22, CAN_TX_B BCM23.
- `test_can_protocol.py` — unit tests for packing/CRC.
- `requirements.txt` — Python dependencies.

### STM32 (`stm32_zephyr/`)

- `src/main.c` — Zephyr tasks and message dispatch, including a separate priority-2 relay thread on N2. Build N2 or N3 separately. All physical output is LED/GPIO-only.
- `src/can_protocol.c/.h` — matching CRC and heartbeat/fault/force frame encoders.
- `src/timing_trace.c/.h` — named physical GPIO probes.
- `src/timing_stats.c/.h` — low-overhead cycle-counter measurement; console reports observed maxima and counts for task bodies.
- `boards/nucleo_f401re.overlay` — dual MCP2515 devices and suggested test-point/button GPIO mapping.
- `prj_n2.conf`, `prj_n3.conf` — zone selection.

### Measurements (`measurements/`)

- `analyze_timing.py` — summarizes CSV events, observed Pi UDP-to-CMD_TX latency, send-call duration, and event inter-arrivals. It does not manufacture missing samples or claim formal WCET.
- `measurement_guide.md` — practical probe setup and handout measurement checklist.

## Protocol assumptions that must be confirmed

The handout specifies 8-byte classic CAN frames, byte 0 as 4-bit sequence + 4-bit flags, and a CRC-8, but does **not** specify the CRC polynomial or exact field bit/byte layout for every message. This starter makes explicit choices so the software is internally consistent:

- CRC-8/ATM: polynomial `0x07`, init `0`, no reflection, xorout `0`, over bytes 0–6; byte 7 contains the CRC.
- CTRL: byte 0 seq/flags, bytes 1–2 signed little-endian steering, byte 3 throttle percent (0–100), byte 4 brake percent (0–100), byte 5 low 8 button bits, byte 6 reserved zero, byte 7 CRC.
- BLINK: byte 1 mode (off/left/right/hazard), byte 2 phase bit, bytes 3–6 monotonic phase epoch in milliseconds, byte 7 CRC.
- HB: byte 1 zone state, byte 2 bus health bits (bit 0 A, bit 1 B), remaining bytes reserved zero.
- FAULT: byte 1 source zone, byte 2 reason (0 = clear request; 1 = test button; 2 = bad CRC; other values reserved), bytes 3–6 detail.
- FORCE: byte 1 signed dummy counter, remaining bytes reserved zero.
- Wheel button convention in this starter: bit 0 test button, bit 1 left, bit 2 right, bit 3 hazard. **Adjust this mapping to your actual wheel buttons.**

Confirm these assumptions with your team/TA and freeze the byte layout before collecting report measurements. A change in CRC/layout must be made in both `pi/can_protocol.py` and `stm32_zephyr/src/can_protocol.c`.

## Wiring assumed by the overlay

**Handout erratum:** on the XIAO CAN expansion board, **D9 is MISO and D10 is MOSI**, opposite the Lab 3 v1.0 handout's table. Use the [corrected Pi/Nucleo mapping and manufacturer sources](../../doc/STM32_PINOUT.md#lab-3-handout-erratum-can-module-mosimiso-are-reversed). This applies to both modules on every node; host SPI pinctrl assignments below remain unchanged.

Per Lab 3 handout, each Nucleo uses SPI1 shared by both MCP2515 modules: SCK PA5, MOSI PA7, MISO PA6. Suggested chip-select/interrupt assignments:

| Signal | N2/N3 MCU pin | Header suggestion |
|---|---|---|
| CAN A CS | PB6 | D10 |
| CAN A INT active-low | PA10 | D2 |
| CAN B CS | PC7 | D9 (or free GPIO) |
| CAN B INT active-low | PB5 | D4 |
| Test button, active-low | PA8 | D7 to GND when pressed |

The overlay assigns demo probes to free pins: RX_A PC2, RX_B PC3, TX_A PA0, TX_B PA1, DEG_A PB0, DEG_B PB1, ERR PC0, SRV PC1, PWM_SET PB9, DIR_A PB10, PID PB11, front LEDs PA4/PB8, rear LEDs PC4/PC5, and a dedicated `RELAY_TX` probe on PC6. Check the actual Nucleo header and existing wiring before connecting anything; do not connect these outputs to the actuator driver in demo mode.

The overlay assumes MCP2515 modules have **16 MHz** crystals and uses 1 MHz SPI. Verify the crystal marking. Check the generated devicetree and `dts/bindings/can/microchip,mcp2515.yaml` for your installed Zephyr version; the lab handout explicitly asks you to validate `reg`, `spi-max-frequency`, `int-gpios`, and pinctrl names.

## Raspberry Pi setup

1. Enable SPI in `/boot/firmware/config.txt` and reboot:
   ```ini
   dtparam=spi=on
   dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
   dtoverlay=mcp2515-can1,oscillator=16000000,interrupt=24
   ```
2. Install dependencies and CAN utilities:
   ```sh
   sudo apt install can-utils python3-pip python3-libgpiod
   python3 -m pip install -r requirements.txt
   ```
3. Bring up each bus at 500 kbit/s. Enable bus-off recovery if supported by your kernel:
   ```sh
   sudo ip link set can0 down 2>/dev/null || true
   sudo ip link set can1 down 2>/dev/null || true
   sudo ip link set can0 type can bitrate 500000 restart-ms 100
   sudo ip link set can1 type can bitrate 500000 restart-ms 100
   sudo ip link set can0 up
   sudo ip link set can1 up
   ip -details link show can0
   ip -details link show can1
   ```
4. Confirm 60 ohms across each bus (power off), common ground, and only two 120-ohm terminations per bus. Do not connect bus wires until each node independently reports CAN active.
5. Start the bridge:
   ```sh
   cd pi
   python3 cockpit_bridge.py --mode live --log ../measurements/pi_run.csv
   ```
   For a non-actuating synthetic traffic test with no UDP wheel source:
   ```sh
   python3 cockpit_bridge.py --mode demo --log ../measurements/pi_demo.csv
   ```
   `--trace-gpio` reserves BCM17, BCM27, BCM22, and BCM23. Check them with `gpioinfo` before enabling the option.

## STM32 builds

Use your installed Zephyr workspace/SDK and the exact board target `nucleo_f401re`. Build each image separately:

```sh
APP_DIR="$(pwd)/stm32_zephyr"
west build -b nucleo_f401re -s "$APP_DIR" -d build/n2 -- -DOVERLAY_CONFIG="$APP_DIR/prj_n2.conf"
west build -b nucleo_f401re -s "$APP_DIR" -d build/n3 -- -DOVERLAY_CONFIG="$APP_DIR/prj_n3.conf"
west flash -d build/n2
# Move the USB connection to the other Nucleo, then:
west flash -d build/n3
```

Run the commands from the repository root inside an initialized Zephyr workspace. They pass absolute paths to the zone config fragments. Build logs should show both MCP2515 nodes and the IWDG. The overlay uses the `iwdg` node label; if your Zephyr board DTS names or disables that node differently, resolve that against the installed Nucleo-F401RE DTS before flashing. This starter intentionally fails initialization if the watchdog is unavailable instead of silently pretending the independent watchdog requirement is met.

The `prj.conf` enables the CAN, GPIO, console, and watchdog subsystems. The STM32 firmware assigns priority 1 to CAN dispatch, priority 2 to the N2 relay, priority 3 to button/PID work, priority 4 to heartbeat TX/monitoring, and priority 5 to FORCE_TX (lower numeric Zephyr priority is higher). The STM32 firmware has a 1-second watchdog timeout and feeds it from the 5 ms heartbeat supervisor. A priority-3 recovery thread polls both CAN controllers and calls `can_recover()` after `CAN_STATE_BUS_OFF`; confirm that your installed Zephyr MCP2515 driver supports these APIs and measure restoration after reconnecting the jumper. It reports observed max task-body times in the USB serial console every 250 ms (`OBS_MAX_US ...`) without printing in the CAN callback.

## First bring-up order

1. Build and flash each STM32 with CAN bus wires disconnected. Confirm serial output reports N2/N3 and both CAN devices initialized.
2. Verify `can0` and `can1` each report 500 kbit/s / error-active on the Pi. Then connect common ground and buses with correct termination.
3. Run `candump -t a can0` and `candump -t a can1`; confirm IDs `010`, `020`, `100`, `101`, `102`, `200`, and `300` appear as applicable.
4. Start N1. Both STM32 nodes should leave startup ERROR once they have valid CTRL plus heartbeats from the other zones.
5. Confirm LEDs, GPIO test points, and printed values before measuring timing.
6. Pull only one jumper at a time and confirm the corresponding degraded LED. Then perform the handout's asymmetric relay scenario: N1 disconnected from B, N3 disconnected from A; N2's relay must carry the first-seen frames across the opposite bus.

## Important implementation status / limits

This is an integration starter based on the uploaded Lab 2 source and the Lab 3 handout. The Python protocol tests can run locally; **the Zephyr builds must be validated in your exact installed Zephyr SDK before flashing**. The app assumes the `microchip,mcp2515` driver accepts the overlay properties shown. It needs physical bring-up and likely minor version-specific devicetree/API fixes.

This first demo focuses on the task graph and test points. It does not claim that every checkoff case is already verified: physical jumper recovery, bus-off behavior, end-to-end deadlines, front/rear 1 ms blink skew, and measured timing remain experiments. It also does not include the full Lab 1 multi-zone safety policy beyond the lab's demo error/heartbeat behavior. The STM32 bus-off recovery call is implemented, but its actual behavior depends on the MCP2515 driver version and must be verified on hardware. It never enables the physical steering or motor outputs.

A maximum observed by GPIO or cycle counter is an **observed execution maximum**, not a proven mathematical WCET. For report tables, record the board, firmware revision, load, number of samples, max, p99, and whether the value is measured or assumed.


## Advanced demo candidate

See [`DEMO_CANDIDATE_STATUS.md`](DEMO_CANDIDATE_STATUS.md) for the targeted fixes in this version and the explicit hardware-validation gates that remain. This is a stronger basis for integration testing, but it is not yet a verified checkoff build.
