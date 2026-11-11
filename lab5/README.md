# Lab 5: Time and Consensus

This branch implements Lab 5 on the **Lab 3 Pi + two NUCLEO-F401RE + six CAN-module setup**. It starts from `lab3_can` revision `69c50d5`; the Lab 4 PCB branch is independent. All three nodes have joined, both Nucleos' A/B indicator checks passed, and complete saved histories agree through entry 2434 after repairing a Pi display-replay gap. Initial wheel input cleared error/hazards; intermittent input gaps, remaining fault cases and scope measurements are still open. See the [bring-up record](docs/BRINGUP_2026-11-10.md).

- [Shared writeup](https://docs.google.com/document/d/1kwUk9po3RsTd_NVpE4F1W3hu7zCnjiTFjznqT5k0Chc/edit)
- [Must-dos](https://docs.google.com/document/d/1fM5APOAQwtd3XQw26Jg4HM-Opq8UdlKVwno77f8kpA0/edit)
- [Handout](https://drive.google.com/file/d/1t1by1C3fa68qGf46RoKFRM3L3FZnoXNS/view), released November 9; due **November 18, 2026, 11:59 PM**
- [Protocol, persistence and limitations](docs/DESIGN.md)
- [Pin additions](docs/PINS.md), [checkoff matrix](docs/CHECKOFF.md), [offline verification](docs/VERIFICATION.md)
- [Integration review and capture interpretation](docs/INTEGRATION.md)
- [Optional cloud mirror](cloud/README.md): locally prepared; not deployed.

## What runs where

| Directory | Purpose |
|---|---|
| `core/` | Allocation-free C Raft, committed graph/client API, clock, CAN framing, relay coordinator and flash journal |
| `stm32_zephyr/` | N2/front and N3/rear applications, with the existing Lab 3 control/demo tasks |
| `host/` | C shared-library adapter used by both Pi and desktop tests |
| `pi/` | Cockpit, durable display history and optional asynchronous HTTPS uplink |
| `tests/` | Protocol, storage, network, Pi, cloud and analysis tests; no live GPIO/CAN |
| `tools/analyze.py` | Analysis of real scope edges, candump and committed-log captures |
| `tools/export_ledger.py` | Read-only JSONL snapshot of the Pi's durable display history |

`pi/vehicle` preserves the Lab 3 Python glue with package-relative imports so its `blinker` module cannot collide with Flask's unrelated package. The original Lab 3 files remain unchanged. The MCU application reuses the tracked Lab 2/3 timing and controller sources by path. This is the Lab 3 GPIO/PWM checkoff workload, not new Lab 4 PCB actuator firmware.

## Offline build and test

Use Python 3.12 and a C compiler. From the repository root:

```sh
python -m pip install -r lab5/requirements-host.txt
python lab5/host/build.py
python -m unittest discover -s lab5/tests -v
```

The first command installs host-test dependencies. The second compiles the **same C core** used in firmware into a local shared library. The third runs deterministic tests, including real CAN fragmentation and a serialized bus model. No command opens physical CAN, GPIO or a serial port. On Windows without GCC/Clang, `python -m pip install ziglang==0.14.1` supplies the supported fallback compiler. `CC` can select an existing compiler.

## Nucleo build profiles

Use the team's Zephyr **4.3.0** checkout, matching CMSIS/STM32 modules, and Zephyr SDK **0.17.4**. Set `ZEPHYR_BASE`, `ZEPHYR_SDK_INSTALL_DIR`, and `ZEPHYR_TOOLCHAIN_VARIANT=zephyr` in the build shell. Run from the configured Zephyr workspace, replacing `<repo>` with the checkout path:

```sh
west build -b nucleo_f401re -d <repo>/lab5/build-n2 <repo>/lab5/stm32_zephyr -- '-DEXTRA_CONF_FILE=prj_n2.conf;swap_ab.conf'
west build -b nucleo_f401re -d <repo>/lab5/build-n3 <repo>/lab5/stm32_zephyr -- '-DEXTRA_CONF_FILE=prj_n3.conf'
```

Keep the `-DEXTRA_CONF_FILE=...` argument quoted, including in PowerShell. N2 uses `swap_ab`; N3 does not, according to the latest recorded Lab 3 checkoff wiring. If the physical setup changed, resolve bus labels before selecting a different mapping. `zephyr/zephyr.elf` in each build folder is the matching firmware image. Building does not flash it.

The linker reserves the upper 256 KiB for persistent state. **Ordinary restart/reflash must preserve that area.** Do not use a mass-erase option for a rejoin test. A deliberate pristine-cluster experiment requires stopping all three nodes and clearing all three histories together; see the bench checklist before doing so.

## Pi application

On the Pi, build the native library for the Pi's own architecture (do not copy the Windows DLL), install `pi/requirements.txt`, and retain the working 500 kbit/s CAN configuration. Only one Lab 3/Lab 5 process may own CAN/GPIO.

```sh
python3 -m pip install -r lab5/pi/requirements.txt
python3 lab5/host/build.py
python3 lab5/pi/cockpit5.py --bus-a can0 --bus-b can1
```

**The last command runs live control.** Use it during an authorized bench session after checking the wiring and stopping the old application. `--no-gpio` disables GPIO only; it still sends CAN commands. `--fifo 1` requests the team's previous FIFO scheduling setting and requires the appropriate permission; its benefit must be remeasured for Lab 5. State defaults to `~/.local/state/team4-lab5/` and is guarded against two N1 processes.

Nucleo shell commands: `lab5 network` (committed graph), `lab5 event` (request a diagnostic event), `lab5 log` (committed entries; use while idle). Pi `STATUS` lines show Raft/network state; `COMMIT` lines and `display.sqlite` contain the display history. The original wheel/proxy UDP format remains unchanged.

For the Pi process, `SIGUSR1` requests one Lab 5 EVENT. `SIGRTMIN` and `SIGRTMIN+1` preserve test-button latch/clear semantics. The old Lab 3 GUI's bad-input injection uses different USR semantics; do not use those controls against this application. Keep the existing wheel proxy for normal input.

The Windows launcher accepts `--lab5 --pi <Pi-address>` to open only the course
wheel GUI and input recording, without the old Lab 3 test panel or Lab 2
telemetry windows. Use the existing course-proxy Python environment with PyQt5
and the wheel SDK. It does not start transmission unless Connect is clicked
or `--connect` is explicitly supplied. It does not start or replace the Pi app.

## Shared configuration

Edit only `config.json`, then rebuild both Nucleo images and distribute that same file to the Pi. The generator rejects incompatible node IDs, voting size, log capacity or handout timing values. `default_leader` is `cockpit` or `random`/`none`; `seed` sets repeatable jitter. Debug is on by default. Persisted state takes priority over cold-start defaults.

## Capture analysis

```sh
python lab5/tools/analyze.py edges captures/edges.csv
python lab5/tools/analyze.py candump captures/can.log --decoded-csv captures/decoded.csv
python lab5/tools/analyze.py logs captures/pi-events.csv captures/n2.txt captures/n3.txt
```

The edge CSV has `signal,time_s` columns containing rising edges from **one scope timebase**, with `FL` and `RL` labels. Pairing is one-to-one; missing edges do not silently become a pass. `candump -L any` provides the text format for traffic analysis. Capture prefixes must include index 1 for complete-log comparison; otherwise missing history is reported. Measured results belong with their capture/revision; synthetic test data must not be presented as a vehicle measurement.

The CAN decoder validates CRCs, reassembles RPCs separately on each interface, and reports REF and empty-APPEND intervals, voting observations and capture-quality problems. Its CSV includes decoded term/index/event/source/destination fields. It does not infer a passed timing or fault test from an average interval or the absence of a captured vote.

For a complete Pi history after a restart, export the ledger on the Pi while idle:

```sh
python3 lab5/tools/export_ledger.py ~/.local/state/team4-lab5/display.sqlite captures/pi-history.jsonl
python3 lab5/tools/analyze.py logs captures/pi-history.jsonl captures/n2.txt captures/n3.txt
```

Create `captures/` first and choose new filenames for each experiment. The exporter opens SQLite read-only, refuses to overwrite existing evidence and includes durable entries only; wait for the application's ledger queue to drain and check its errors. Do not copy only `display.sqlite` while it is live: recent committed rows may still be in its WAL file. Export on the Pi or use a consistent SQLite backup. Log equality deduplicates repeated identical serial lines; inspect display/replay behavior separately.
