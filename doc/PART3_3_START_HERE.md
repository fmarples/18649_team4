# Part 3.3 — steering, one small step at a time

**Branch scope:** these are instructions for the separate `lab2-tianyi-steering`
bench. If you checked out `lab2-integration`, use
[the integration guide](INTEGRATION_START_HERE.md) instead: its root firmware
also contains motor control and requires the combined hardware setup.

**Latest power plan (2026-09-26):** Tianyi reports the TA explicitly said to
use 5 V and that it will work. Follow that bench plan with the second fixed-output
HW-688. Its underside labels are VIN+/VIN- and 5V/GND; there is no adjustment
potentiometer. The earlier instruction to adjust it to 6 V was wrong.
See [the exact terminal and multimeter check](HW688_OUTPUT_CHECK.md). Measure
the output before attaching the servo; actual steering performance at 5 V
remains to be tested. No firmware change is needed for the supply choice.

Use Tianyi's **separate LED/servo NUCLEO-F401RE**, not the teammate's motor board.
Branch: `lab2-tianyi-steering`. This includes the corrected Part 3.4 blinkers.
The existing checkout folder still ends in `18649_team4_blinkers`; that is normal.
No motor, encoder or current-sensor implementation is added by this branch.

**Prepared on 2026-09-26:** combined image flashed and verified on this separate
board; boot and disabled-console checks passed. You do not need to build or
flash again for the steps below. See [test evidence](PART3_3_RESULTS.md).

## What is ready, and what you must measure

The firmware generates the servo signal at **D14 / PB9 / TIM4 channel 4**.
It starts with **no PWM pulses**, regardless of the wheel position. Opening
the Windows calibration console also turns PWM off. Only your `arm` command
starts it. The code maps measured left/center/right positions to the Logitech
wheel, supports either servo orientation, and rejects an invalid calibration.

You still need to confirm the actual servo label, its power supply, and the
three safe pulse widths on your chassis. These values cannot be obtained from
the advertised servo angle alone. Hardware timing has not been measured.

The [manufacturer's kit page](https://www.hiwonder.com/products/ackermann-steering-chassis?variant=40382428348503)
lists an **LD-1501MG** servo with **6–8.4 V** operating voltage, **500–2500 us**
command range and **2.4–3 A stall current**. Its
[STM32 tutorial](https://docs.hiwonder.com/projects/Ackermann-Chassis/en/latest/docs/2_STM32_Version_checked.html)
specifies a **20 ms / 50 Hz** period. Compare the actual label before using these
ratings. The TA-approved 5 V bench plan is below that published 6–8.4 V range;
retain that distinction in the report. Verify actual motion under the linkage
load and record the result rather than treating the TA's guidance as a completed
measurement. Do not deliberately stall the servo.

The manufacturer's available specifications do not establish a minimum accepted
logic-high voltage. This Nucleo emits **3.3 V logic**. If the correctly powered
servo does not recognize it, stop and verify signal compatibility/waveform;
a suitable 3.3-to-5 V buffer may be needed. Never apply 6 V or 12 V to D14.

## 1. Prepare power before connecting the servo

**Inventory update:** use the second fixed nominal 5 V HW-688 for the servo,
following the TA's guidance. Preserve the existing STM32 power arrangement.

1. Leave the motor teammate's board and firmware alone. Support the chassis so
   it cannot drive away; keep its motor-power branch off for your steering test.
2. Locate the servo's label. If it is not LD-1501MG, check its own rating first.
3. With the lab 12 V adapter unplugged, wire its positive DC output to the second
   converter's VIN+ and its negative DC output to VIN-. These are the blue input
   terminals beside the black barrel jack. Use the printed underside labels.
   The output blue terminals beside USB are 5V and GND. Keep the servo detached.
4. Power the converter and measure from output 5V (red probe) to GND (black),
   using the photographed MN35's 20 V DC range. Expect about 5–5.2 V; no screw
   adjustment is involved. Unplug the adapter before attaching the servo.
   The shared 12 V, 2 A source is not yet validated for simultaneous motor/servo
   loads; keep the motor-power branch off for this steering bench test.
5. Turn supplies off before adding wires. Preserve this bench board's existing
   working power arrangement; do not assume it uses the motor board's E5V setup.

## 2. Connect the three servo wires

Hiwonder's stock wiring is white signal, red positive and black ground. Check
the actual connector rather than trusting replacement-cable colors.

| Servo connection | Goes to |
| --- | --- |
| White signal | Nucleo **D14**, which is **PB9** |
| Red positive | Second HW-688 terminal labeled **5V** |
| Black ground | Separate supply ground **and Nucleo GND** |

The Pi and Nucleo retain the shared ground from the working UART link.
**D15 is the blue rear-right LED. D14 is the servo.** No servo power wire goes
to a GPIO, the Nucleo 3V3 rail, or directly to the 12 V motor rail. Route servo
power through suitable power wiring, not a long chain of signal jumpers.

After wiring, power the Nucleo normally, then the separate servo supply. Keep
hands clear: even without command pulses, a servo may twitch during power-up.
Have its supply switch/connector accessible. Removing servo power is the
physical stop; removing PWM alone does not guarantee zero holding torque.

Connect the servo's black wire directly to the converter's GND output junction,
then add a separate wire from that junction to Nucleo GND. The servo's power
return must not pass through the Nucleo. Use a suitable terminal junction and
servo extension/breakout for a three-position servo plug; do not force loose
wires into its female contacts or cut the connector to make it fit.

## 3. Open the calibration console on Windows

Close any miniterm/serial monitor using the Nucleo's COM port. The wheel proxy
can stay open; it does not own this serial port.

In a **Windows Command Prompt**, paste this exact command:

```bat
"C:\Users\hetia\CMU\18649\18649_team4_blinkers\windows\start_servo_console.cmd"
```

The tool identifies this bench board by ST-LINK serial
`066BFF485270535067124020`, rather than guessing from a changing COM number.
It should print `OFF: pulse=0 us` and a `servo>` prompt. Leave this window open
through calibration and live testing. No Pi connection is needed yet.

If it says no firmware reply, stop here: the combined steering image must be
on the separate board. If the port is busy, close the other serial monitor.
Do not reset or flash the teammate's motor board to resolve this.

## 4. Find straight ahead

Only after the power/wiring checks above, type and press Enter:

```text
arm
```

This applies **1500 us**, a nominal electrical midpoint, not a proven mechanical
center. Watch the linkage. If it presses against a stop, buzzes or strains,
type `off` and remove servo power immediately. Do not keep trying stronger
commands against a stop. Correct horn/linkage alignment with power off if needed.

To change the position, type one command at a time:

```text
+
```

increases pulse width by **25 us**. `-` decreases it by 25 us. `+5` and `-5`
make finer **5 us** changes. These signs mean pulse width, not car direction.
Observe which way your front wheels move. Do not hold the wheels by hand.

When the front wheels point straight ahead, type:

```text
center
```

That records the current pulse as straight ahead. It does not move the servo.

## 5. Find the two safe endpoints

1. Use individual `+` or `-` commands to move toward the **car's left**, as seen
   by a driver facing forward. Watch the linkage after each command.
2. Near its travel limit, use `+5`/`-5`. Stop before mechanical binding. Never
   keep stepping until the advertised 500 or 2500 us just to reach that number.
3. Back away slightly if it approaches a hard stop. At the farthest safe,
   strain-free left position, type `left` to record it.
4. Type `home` to return to your recorded center.
5. Move gradually toward the **car's right**. Find the safe endpoint the same
   way, then type `right`.
6. Type `home`, then `status`. It should show `calibration=READY` with three
   distinct values. The center must be between the endpoints numerically.
   Left may be the larger value; the mapping handles that.
7. Type `save`. The tool saves your measured values to:

```text
C:\Users\hetia\CMU\18649\18649_team4_blinkers\logs\part3_3\calibration.json
```

Calibration in the MCU is RAM-only. `save` preserves it on the laptop across
resets. If calibration is refused, recheck which position you marked; do not
substitute guessed endpoint values. Send the final three values to your teammate.

## 6. Connect the real Logitech wheel through the Pi

Keep the calibration console open. The Pi bridge and wheel proxy are separate
programs. If they are already running successfully, leave them running.

Update the Pi's status decoder once for the new self-test state. In another
**Windows Command Prompt**, run:

```bat
scp "C:\Users\hetia\CMU\18649\18649_team4_blinkers\pi\part2_protocol.py" labuser@172.26.166.33:~/18649/part2/
ssh labuser@172.26.166.33
```

Enter the Pi login password locally. These use the last confirmed CMU-DEVICE
address; if it changes, use the current Pi address in both commands.

At the **Pi** prompt, run:

```bash
cd ~/18649/part2
python3 part2_bridge.py --mode live
```

Run only one bridge process. Stop an older one with Ctrl+C first if necessary.

In another **Windows Command Prompt**, start the wheel proxy:

```bat
"C:\Users\hetia\CMU\18649\18649_team4_blinkers\windows\start_wheel_proxy.cmd"
```

Enter `172.26.166.33` when it asks for the Pi address. Clamp the Logitech wheel,
keep hands clear of its connection bump, click **connect**, and leave **Toggle
feedback** alone. The Pi should show changing steering input and `LINK_OK`.

## 7. Follow the Logitech wheel

1. Put the Logitech wheel near its center. The allowed start window is raw
   steering -2000 through +2000. Keep the car wheels at your saved center.
2. In the calibration console, type `live`.
3. Expect `LIVE`. Turn the Logitech wheel **slowly** left, back to center,
   right, then center. The car wheels should follow the same direction smoothly
   without reversals, buzzing or mechanical strain.
4. If direction is reversed, type `off`, then recalibrate with `left` and
   `right` referring to the actual car directions. Do not change the Pi axis
   sign just to hide a mislabeled calibration.
5. Stop with `off`. To use live control again: `arm`, center the Logitech wheel,
   then `live`. Type `quit` when finished, then turn off the servo supply.

`live` is refused if calibration is incomplete, the wheel is off-center, the
Pi link is unhealthy, or self-test is active. A fault disables live PWM and
requires deliberate re-arming after recovery. Manual calibration intentionally
works without a Pi link, but self-test and loss of the USB console heartbeat
still disable it. Do not use manual mode as the final car operating mode.

## 8. Quick start next time

Use the same servo/linkage and verified power arrangement. Start the Pi bridge,
wheel proxy and Windows servo console as above. At `servo>` enter:

```text
load
arm
```

Center the Logitech wheel, then enter:

```text
live
```

`load` reads your saved JSON and does not move the servo. `arm` applies its
center. Recalibrate if the horn, linkage or servo has changed.

## 9. Recheck the corrected Part 3.4 self-test

- Startup or loss of valid commands: all four hazard LEDs flash.
- Healthy commands: hazards clear; paddles still select left/right signals.
- **G920 A button, one press:** latch self-test, hazards flash; servo PWM stops.
- **A double press within 400 ms:** clear the manual latch. A real link fault
  still keeps hazards active. Servo stays OFF until deliberately re-armed.

This board does **not** have the motor H-bridge attached. The motor teammate
must use the same fault condition to command physical dynamic braking, not
simply coast. No motor-braking checkoff has been established here.

## 10. What to record for the handout

| Item | Your evidence |
| --- | --- |
| Actual servo model and power source | Label, supply rating, measured voltage |
| Command period | Intended 20 ms; verify on scope/analyzer later |
| Safe left / straight / right pulses | Your saved calibration JSON |
| Physical linkage limits | Observed travel; angle measurement/photo if required |
| Monotonic left → center → right → center | Short video or observation record |
| Endpoints free of strain/buzzing | Physical observation, not code output |
| Response within 50 ms (R2.3) | Still requires measured evidence |

The code bounds requests to the manufacturer's 500–2500 us range, then maps
live steering only between your narrower measured endpoints. It does **not**
intentionally test out-of-range commands. The physical servo's behavior outside
its specified range is undocumented in the retrieved sources; do not claim a
measured response or force it there to find out.

The mapping is piecewise linear: raw -32768 maps to measured left, 0 to center,
and +32767 to measured right. The negative and positive halves use their own
spans, preserving center even if travel is asymmetric. Digital pulse resolution
makes the mapping non-strictly monotonic (nearby raw values can share a pulse).

## Integration handoff

Keep `servo_core.c/.h` (mapping, calibration/interlocks) and TIM4/PB9 allocation.
`servo_bench.c` plus the USB heartbeat are temporary bench controls. The final
single-MCU firmware should explicitly adopt measured calibration and a reviewed
fault/recovery policy, without requiring this development console to drive.
The binary Pi command/status frame layout is unchanged; state 5 is SELF_TEST.
The existing status axes are command readbacks, not measured servo angles.

Build on this Windows host from the Zephyr workspace:

```powershell
$env:Path='C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts;' + $env:Path
$env:ZEPHYR_SDK_INSTALL_DIR='C:\Users\hetia\zephyr-sdk-1.0.1'
cd C:\Users\hetia\CMU\18649\zephyrproject
west build -b nucleo_f401re C:\Users\hetia\CMU\18649\18649_team4_blinkers\stm32_zephyr -d C:\Users\hetia\CMU\18649\18649_team4_blinkers\build\blinkers
```

The retained build-directory name `blinkers` now contains the combined image
on the steering branch. Flash only the explicitly identified separate board.
