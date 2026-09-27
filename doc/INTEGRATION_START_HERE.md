# Motor, blinker and steering integration

**Part 4 update:** use [the current meeting guide](../PART4_START_HERE.md) and
[actual task table](../PART4_TASK_TABLE.md). The merge/build details below are
the earlier integration baseline. Part 4 now adds timing GPIOs, a dedicated
current-sampling workqueue with unavailable backend, and a 60 ms UART timeout.
Use `build/part4` for the new image, and deploy all `pi/*.py` files together.
Tianyi reports 3.3 and 3.4 individually tested; combined tests remain pending.

Branch: **lab2-integration**. Base: main commit `983cb1b`; merged steering branch
commit `1d11ef2`, which already includes the blinkers. Main and the standalone
bench branches remain unchanged. The combined image has not been flashed or
tested on the physical car. This guide supersedes the standalone guides when
using this integration branch.

## What is combined

- Main's Pi/CRC link, encoder decoding, pedal mapping, motor PID and L298N driver.
  Existing 1320 counts/revolution, 23..300 RPM active targets, 60%/200 ms startup,
  40..100% running PWM, continuous PID and B1 latch are preserved.
- Left/right paddle blinkers, automatic cancellation on steering return, startup
  and fault hazards, and A/button 0 self-test.
- The opt-in steering console and PB9/D14 servo output, initially OFF.
- Tracked [servo calibration](../config/servo_calibration.json): **left 1200 us,
  center 1600 us, right 2000 us**, with a 20000 us period. The user chose these
  numbers; neither physical endpoint safety nor successful live tracking has
  been confirmed. Changing the linkage requires checking them again.

## Integration conflicts resolved

| Conflict | Resolution |
| --- | --- |
| Different main loops/build lists | Main owns validation and all actuator updates; all required sources are linked. |
| Status 5 used twice | Keep 5 = ERROR_MOTOR; 6 = SELF_TEST; 7 = ERROR_ACTUATOR. Update Pi decoder with this firmware. |
| PA5 link indicator versus right-front lamp | Remove link-indicator writes. PA5/D13 and onboard LD2 follow the right blinker. |
| Steering bench disabled pwm2 | Keep TIM2/PB10 enabled for the right motor; TIM3/PB4 for left motor; TIM4/PB9 for servo. |
| Self-test previously had no motor output | A first press now requests dynamic braking, hazards and servo OFF in the combined owner. |
| USB reply prints in actuator owner | Queue normal replies to the lower-priority diagnostic thread; motor updates do not wait for those prints. |

Motor/B1 faults also select hazards and disable steering. B1 retains main's
latched enable-low/coast behavior. Self-test and transport faults dynamically
brake a healthy motor driver. A servo/lamp output API failure latches an actuator
fault, disables servo PWM and requests braking. Reset is needed for a latched
hardware fault. A failed output peripheral cannot guarantee its physical output.

Clearing self-test with an A double press within 400 ms restores motor response
to the current pedals when no real fault remains. Release throttle before that
test. Servo stays OFF until explicitly re-armed. No full-vehicle automatic
steering start policy was introduced by the merge.

## Before a combined hardware test

1. Preserve the already-tested separate servo/blinker setup. Check its mapping
   again after moving signals onto the final motor board or changing mechanics.
2. Use the final motor/encoder Nucleo and the [pin table](STM32_PINOUT.md) to
   integrate the servo and four LEDs physically. Change wiring with power off.
   The two existing Nucleos are separate bench setups; merging software does
   not connect them. This image expects the motor encoders, B1 and output pins.
3. Follow the confirmed E5V/USB sequence in [HARDWARE.md](HARDWARE.md). The
   shared supply's simultaneous load performance remains unverified. The
   previously discussed shared converter wiring is not established by this merge.
4. Confirm the target ST-LINK identity before a later authorized flash. The
   integrated motor code can respond to fresh throttle commands immediately;
   the servo console's `off` command only stops servo PWM, not the motors.
5. After that deployment, copy **both** `pi/part2_bridge.py` and
   `pi/part2_protocol.py` to the Pi's existing `~/18649/part2/` directory. Run
   one bridge process and the wheel proxy. Old state 5 on the steering-only
   firmware is incompatible with the new decoder's meaning of state 5.

For the optional `pi/blinker_check.py` visual sequence, also use the version
from this branch, stop the live bridge, and issue servo `off` first. The
sequence injects steering commands while keeping throttle released and brake
pressed; an already-LIVE servo would otherwise follow those commands.

## Load the tracked calibration

On Tianyi's machine the new checkout is:

```text
C:\Users\hetia\CMU\18649\18649_team4_integration
```

The console still auto-selects Tianyi's separate bench ST-LINK serial. For
another intentionally selected Nucleo, use its verified COM port explicitly:

```bat
"C:\Users\hetia\CMU\18649\18649_team4_integration\windows\start_servo_console.cmd" --port COM_NUMBER
```

Replace `COM_NUMBER` with the actual port; close other serial monitors first.
At `servo>`:

```text
off
load
status
```

These commands do not move the servo. The helper prints the file it loaded:
it prefers `logs/part3_3/calibration.json` if present, otherwise the tracked
`config/servo_calibration.json`. An invalid local file is rejected rather than
silently replaced. `save` writes only the local file; it does not edit the team
preset. `--file` can select a specific calibration without a fallback.

When ready for a physical steering test, center the Logitech wheel and enter
`arm` (moves to 1600 us), then `live` with a healthy Pi link. Keep the console
open: its 500 ms heartbeat is still required. Lost LIVE input, self-test and
hardware faults disable steering; there is no automatic re-arm. This branch
still needs an explicit design change before console-independent operation.

## Software checks

On Tianyi's installed Zephyr environment:

```powershell
$env:Path = 'C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts;C:\Program Files\Git\mingw64\bin;' + $env:Path
$env:ZEPHYR_SDK_INSTALL_DIR = 'C:\Users\hetia\zephyr-sdk-1.0.1'
$integrationRepo = 'C:\Users\hetia\CMU\18649\18649_team4_integration'
Set-Location 'C:\Users\hetia\CMU\18649\zephyrproject'
west build -b nucleo_f401re "$integrationRepo\stm32_zephyr" -d "$integrationRepo\build\integration"
west build -b qemu_cortex_m3 "$integrationRepo\tests\integration" -d "$integrationRepo\build\integration-tests"
west build -d "$integrationRepo\build\integration-tests" -t run
Set-Location $integrationRepo
python -m unittest discover -s tests -p 'test_*.py' -v
python test_protocol.py -v
```

The QEMU suite runs the actual C blinker, self-test and servo logic, new combined
fault/stop tests, and main's existing C motor/PID/bench/throttle regression
contracts. It does not drive hardware. Native host-GCC cases may be skipped
when GCC is absent; their C contracts are also run by the ARM/QEMU suite.
Logs are under `logs/integration/` (ignored by Git).

Verified for this merge:

- `nucleo_f401re` build succeeded using Zephyr
  `v4.4.0-16655-g7a7003dec4b9` and SDK 1.0.1. Image uses 58,488 bytes of flash
  and 12,416 bytes of RAM.
- Firmware `zephyr.bin` SHA-256:
  `56c780a1167847f63619a629888177240e9ed4f52a9d978822cd6c69ff4f0901`.
- ARM/QEMU: **36 tests passed** across combined actuator policy (5), blinkers
  (12), existing motor/PID/bench/throttle contracts (4), self-test (8), and
  steering (7). QEMU printed `PROJECT EXECUTION SUCCESSFUL`; the emulator was
  then stopped. The initial run exhausted the test harness's default stack;
  the passing run used an 8192-byte ztest stack with stack-sentinel checking.
  This does not change the production firmware's stack sizes.
- Python discovery: **35 passed, 2 skipped** because native host GCC is absent.
  The skipped C-controller contracts are covered by QEMU above. The separate
  protocol suite passed all **9 tests**. Calibration helper tests also passed
  after the final metadata edit; the updated blinker script passed syntax checking.
- Compiled devicetree confirms left/right motor PWM on TIM3/PB4 and TIM2/PB10,
  servo PWM on TIM4/PB9, and lamps on PB6/PA4/PA5/PB8. No motor/PID/encoder
  implementation files or motor bring-up profiles were changed by this merge.

Physical PWM/response timing, braking, LED waveforms, actual servo angle and
combined-board behavior still require hardware checks. ADC/current sensing
remains absent; status continues reporting unavailable current, not fake zeros.
