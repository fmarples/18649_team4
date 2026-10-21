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

- `src/main.c` — Zephyr measurement workers and message dispatch, with an optional Part 4 relay thread on N2. Build N2 or N3 separately. All physical output is LED/GPIO-only.
- `src/can_protocol.c/.h` — matching CRC and heartbeat/fault/force frame encoders.
- `src/timing_trace.c/.h` — named physical GPIO probes.
- `src/timing_stats.c/.h` — cycle-counter elapsed measurements, raw-cycle maxima and sample counts.
- `src/timing_probe.c/.h` — serial-shell selection of one task's PC8 scope pulse.
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

**Handout erratum:** on the XIAO CAN expansion board, **D9 is MISO and D10 is MOSI**, opposite the Lab 3 v1.0 handout's table. Use the [corrected Pi/Nucleo mapping and manufacturer sources](../../doc/LAB3_PINOUT.md#lab-3-handout-erratum-can-module-mosimiso-are-reversed). This applies to both modules on every node; host SPI pinctrl assignments below remain unchanged.

Per Lab 3 handout, each Nucleo uses SPI1 shared by both MCP2515 modules: SCK PA5, MOSI PA7, MISO PA6. Suggested chip-select/interrupt assignments:

| Signal | N2/N3 MCU pin | Header suggestion |
|---|---|---|
| CAN A CS | PB6 | D10 |
| CAN A INT active-low | PA10 | D2 |
| CAN B CS | PC7 | D9 (or free GPIO) |
| CAN B INT active-low | PB5 | D4 |
| Test button, active-low | PC13 | Built-in blue B1 button |

The overlay assigns demo probes to free pins: RX_A PC2, RX_B PC3, TX_A PA0, TX_B PA1, DEG_A PB0, DEG_B PB1, ERR PC0, SRV PC1, PWM_SET PB9, DIR_A PB10, PID PB11, front LEDs PA4/PB8, rear LEDs PC4/PC5, a dedicated `RELAY_TX` probe on PC6, and a selectable task-body probe on PC8. Check the actual Nucleo header and existing wiring before connecting anything; do not connect these outputs to the actuator driver in demo mode.

The overlay assumes MCP2515 modules have **16 MHz** crystals and requests the MCP2515 maximum SPI clock of 10 MHz. With the 84 MHz SPI1 source, Zephyr selects 84/16 = 5.25 MHz; an October 21 scope capture measured a 190.79 ns mean SCK period. Through October 21, earlier builds requested 1 MHz and ran at 656.25 kHz. Verify the crystal marking. Check the generated devicetree and `dts/bindings/can/microchip,mcp2515.yaml` for your installed Zephyr version; the lab handout explicitly asks you to validate `reg`, `spi-max-frequency`, `int-gpios`, and pinctrl names.

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
west build -b nucleo_f401re -s stm32_zephyr -d build/n2 -- -DEXTRA_CONF_FILE=prj_n2.conf
west build -b nucleo_f401re -s stm32_zephyr -d build/n3 -- -DEXTRA_CONF_FILE=prj_n3.conf
```

These source paths are relative to this variant directory, `lab3_wcet_baseline/lab3_wcet_baseline`, in an initialized Zephyr environment. Do not flash by an ambiguous default probe when both boards are connected. The user waived diagnostic backup; rejected readbacks are not valid recovery images. Build logs should show both MCP2515 nodes and the IWDG. The overlay uses the `iwdg` node label; if your Zephyr board DTS names or disables that node differently, resolve that against the installed Nucleo-F401RE DTS before flashing. This starter intentionally fails initialization if the watchdog is unavailable instead of silently pretending the independent watchdog requirement is met.

Both variants compile with Zephyr 4.3.0. The workers wait for successful hardware setup. The heartbeat supervisor runs every 20 ms and feeds the 1-second watchdog. The installed MCP2515 driver does not implement manual recovery; that task is excluded, and hardware bus-off recovery remains unverified. Named `OBS_TASK` records print every five seconds. See [measurement definitions and scheduling caveats](README_WCET_BASELINE.md) before using the values. The Part 4 relay is disabled unless `CONFIG_LAB3_RELAY=y` is explicitly selected on N2.

## First bring-up order

1. Build and flash each STM32 with CAN bus wires disconnected. Confirm serial output reports N2/N3 and both CAN devices initialized.
2. Verify `can0` and `can1` each report 500 kbit/s / error-active on the Pi. Then connect common ground and buses with correct termination.
3. Run `candump -t a can0` and `candump -t a can1`; confirm IDs `010`, `020`, `100`, `101`, `102`, `200`, and `300` appear as applicable.
4. Start N1. Both STM32 nodes should leave startup ERROR once they have valid CTRL plus heartbeats from the other zones.
5. Confirm LEDs, GPIO test points, and printed values before measuring timing.
6. Pull only one jumper at a time and confirm the corresponding degraded LED. Then perform the handout's asymmetric relay scenario: N1 disconnected from B, N3 disconnected from A; N2's relay must carry the first-seen frames across the opposite bus.

## Important implementation status / limits

This is a measurement starter based on the uploaded Lab 2 source and the Lab 3 handout. N2 and N3 compile with Zephyr 4.3.0 and have been flashed, boot-checked and measured on target. GPIO probes, shell selection and catalog traffic were exercised. Selected results and remaining coverage are in [the timing ledger](../../doc/LAB3_TIMING_RESULTS.md); this is not full checkoff validation.

This variant provides measurement workers and test points. It does not claim that every checkoff case is already verified: physical jumper recovery, bus-off behavior, end-to-end deadlines, front/rear 1 ms blink skew, and measured timing remain experiments. It also does not include the full Lab 1 multi-zone safety policy beyond the lab's demo error/heartbeat behavior. The installed MCP2515 driver has no manual-recovery API; restoration behavior must be verified on hardware. It never enables the physical steering or motor outputs.

A maximum observed by GPIO or cycle counter is an **observed execution maximum**, not a proven mathematical WCET. For report tables, record the board, firmware revision, load, number of samples, max, p99, and whether the value is measured or assumed.


## WCET baseline profile

See [`README_WCET_BASELINE.md`](README_WCET_BASELINE.md) for the measurement-first workflow, interpretation of observed maxima, and limitations retained intentionally in this baseline.
