# Part 4: tomorrow at 10 AM, step by step

Use branch **lab2-integration**. This guide is for the combined **motor Nucleo**.
Tianyi reports steering (3.3) and blinkers (3.4) already tested on their separate
bench. Preserve that working setup until the team is ready to connect all
outputs to one board. Part 3.5 current sensors are unfinished.

The software has been prepared without commanding, flashing or connecting to
your hardware. Timing and combined-car tests below are tasks for the meeting.

## 1. Agree on roles before powering up

- **Tianyi:** integration firmware, laptop wheel proxy, Pi bridge, logs and task table.
- **Motor teammate:** confirm the final motor/encoder code and 3.1/3.2 results;
  own the physical motor setup and emergency stop during combined tests.
- **Third teammate:** current sensors (3.5); help label the scope probe board and
  save measurements. Use [the sensor handoff](doc/CURRENT_SENSOR_HANDOFF.md).

Ask the motor teammate whether anything changed after main commit `983cb1b`.
This integration includes that motor code. If there are newer motor changes,
merge/review them before flashing; don't discard their work or replace their
working branch. All three should be able to explain the task table.

## 2. Open the correct folder on Tianyi's Windows laptop

Open **PowerShell**, then paste:

```powershell
$repoPath = 'C:\Users\hetia\CMU\18649\18649_team4_integration'
Set-Location $repoPath
git status --short --branch
git log -1 --oneline
```

Expected branch: `lab2-integration`. If there are local changes you don't
recognize, keep them and resolve with the teammate before pulling/flashing.

To retrieve future updates when this checkout is clean:

```powershell
git pull --ff-only
```

Rebuild the exact checkout before deployment. This only builds; it does not flash:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\build_part4.ps1
```

Expected ending: generated pin/configuration checks pass, followed by the
firmware SHA-256. Binary: `build\part4\zephyr\zephyr.bin`.
Use **part4**, not the older `build\integration` directory.

## 3. Combine wiring, with all power off

Keep the verified motor/encoder wires. Move the tested servo signal and four
LED signal wires onto the **same motor Nucleo**:

| Function | Final board socket |
| --- | --- |
| Servo signal | D14 / PB9 |
| Front-left red LED | D10 / PB6 |
| Rear-left yellow LED | A2 / PA4 |
| Front-right white LED | D13 / PA5 |
| Rear-right blue LED | D15 / PB8 |
| Pi TX, physical pin 8 | D2 / PA10 |
| Pi RX, physical pin 10 | D8 / PA9 |
| Pi ground, physical pin 6 | STM32 GND |

Keep each LED's 470-ohm resistor and polarity. Servo power stays on the
TA-approved external 5 V arrangement; its ground joins the common signal
ground. GPIO only supplies the servo signal. Do not connect the two boards'
GPIO outputs together or connect a motor terminal to the Pi/STM32.

Use [STM32_PINOUT](doc/STM32_PINOUT.md) and [HARDWARE](doc/HARDWARE.md) for
the existing motor connections and E5V power-selection details. The tested
servo/blinker setup does not by itself prove the shared supply handles every
load simultaneously.

Build the labeled 13-row probe board using [PART4_TIMING](doc/PART4_TIMING.md).
That guide identifies the new PC2/PC3 and Pi BCM17/27 marker wires. Leave the
current sensor analog inputs unconnected until the 3.5 teammate confirms safe
voltage conditioning and actual sensor wiring.

## 4. Identify the board, then flash the built firmware

Keep wheels raised and the wheel proxy stopped. Follow the motor board's
confirmed sequence: external E5V on first, ST-LINK USB second; JP5 on E5V,
JP1 open. Have **only the intended final Nucleo connected by USB** for this step.

In the same PowerShell:

```powershell
Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,VolumeName
& 'C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts\python.exe' -m serial.tools.list_ports -v
```

Write down the final Nucleo's drive letter, COM port and ST-LINK identity.
COM11 was Tianyi's separate board previously; don't assume it is the motor board.

The next block asks for the **drive letter you just verified**, for example
`D:`. It verifies the volume label, then programs/restarts that Nucleo:

```powershell
$nucleoDrive = (Read-Host 'Verified NOD_F401RE drive letter, including colon').Trim().ToUpper()
$volume = Get-CimInstance Win32_LogicalDisk | Where-Object DeviceID -eq $nucleoDrive
if ($volume.VolumeName -ne 'NOD_F401RE') { throw 'Stop: that is not the verified Nucleo drive.' }
Copy-Item -LiteralPath "$repoPath\build\part4\zephyr\zephyr.bin" -Destination ($nucleoDrive + '\lab2.bin')
```

Wait for the board to finish programming. Inspect its USB drive for `FAIL.TXT`.
If present, read it and resolve that error. File copying alone is not proof of
a successful flash; the next serial/functional checks establish the running image.
This image can respond to throttle commands as soon as the Pi link is healthy.

## 5. Open the USB servo/diagnostic window

In that PowerShell window:

```powershell
$nucleoPort = Read-Host 'Verified final Nucleo COM port, for example COM11'
$usbLog = Join-Path $repoPath ('logs\part4\usb-' + (Get-Date -Format yyyyMMdd-HHmmss) + '.log')
& "$repoPath\windows\start_servo_console.cmd" --port $nucleoPort --log $usbLog
```

At the `servo>` prompt type these individually, pressing Enter after each:

```text
off
load
status
diag
```

Expected:
- Servo mode **OFF**, calibration **1200 / 1600 / 2000**, valid/READY.
- `diag` shows recent STM, DRIVE and DIAG lines. No Pi traffic yet means a
  waiting/error state, hazards, and motor **mode=2** (dynamic-brake request).
- `trace_errors=0`, `servo_error=0`, `lamp_error=0`.
- The motors should not propel the car. Physically verify the driver's brake
  behavior/pin state; a printed mode is only the requested software state.

Keep this window open. It is the servo's heartbeat source and records USB logs.
Do not open miniterm on the same COM port. `off` and `quit` only stop servo PWM;
they are **not motor-stop commands**. Use the brake pedal/A self-test, or the
existing B1 latched coast stop as appropriate.

## 6. Put the matching Pi files in place

Open **a second PowerShell window**. Set these values again (variables don't
carry across windows):

```powershell
$repoPath = 'C:\Users\hetia\CMU\18649\18649_team4_integration'
$piAddress = Read-Host 'Pi address; last known CMU-DEVICE address was 172.26.166.33'
ssh "labuser@$piAddress"
```

You are now at `labuser@wheelpi`. If Wi-Fi's address changed, find the actual
address using the existing direct-Ethernet/monitor connection and:

```bash
nmcli device status
nmcli -g IP4.ADDRESS device show wlan0
```

Use only the IPv4 address without `/17` in SSH/proxy commands. Registration
does not replace checking the live connection.

On the Pi, stop any old bridge with Ctrl+C in the terminal running it. Check:

```bash
pgrep -af 'part2_bridge.py|wheel_monitor_readonly.py|proxy_receiver'
mkdir -p ~/18649/part2 ~/18649/backups
cp -a ~/18649/part2 ~/18649/backups/part2-$(date +%Y%m%d-%H%M%S)
exit
```

After `exit`, you are back in Windows PowerShell. Copy all matching Python
files, including the **new timing_gpio.py dependency**:

```powershell
scp "$repoPath\pi\*.py" "labuser@${piAddress}:18649/part2/"
ssh "labuser@$piAddress"
```

Back on the Pi, for a first functional test:

```bash
cd ~/18649/part2
mkdir -p logs
python3 part2_bridge.py --mode live --log "logs/part4-$(date +%Y%m%d-%H%M%S).csv"
```

Expected: it waits for wheel UDP; once connected to the flashed board it prints
STM status. All three current readings should say **UNAVAILABLE** for now.
Keep this window open. Don't simultaneously run a second bridge or UART receiver.

For timing measurements later, stop this process with Ctrl+C, perform the
libgpiod setup in PART4_TIMING, and restart with:

```bash
python3 part2_bridge.py --mode live --trace-gpio --log "logs/part4-timing-$(date +%Y%m%d-%H%M%S).csv"
```

If GPIO access is denied, check membership of the Pi's gpio group or run this
known script with sudo after verifying the requested chip/lines. Do not silently
claim Pi markers are active when running without `--trace-gpio`.

## 7. Start the Logitech proxy in a third window

Open **a third PowerShell window**:

```powershell
& 'C:\Users\hetia\CMU\18649\18649_team4_integration\windows\start_wheel_proxy.cmd'
```

Enter the Pi's current address. Keep the wheel clamped and hands clear of its
connection bump; click **connect** in the small course GUI. Leave feedback alone.
Release the throttle and brake pedals and center the Logitech wheel.

Expected in the Pi window: **LINK_OK**, brake/throttle near 32767, steering near
zero. In the servo window, `diag` should report motor **mode=0** (released pedal
coast) and no faults. Blinkers should leave startup hazards.

## 8. Enable already-calibrated steering and check combinations

In the servo window:

```text
arm
live
status
```

`arm` moves toward the saved center, 1600 us. `live` follows the Logitech wheel
only when centered, linked and free of faults. Expected mode: **LIVE**.

Test one item at a time, then together:

1. Wheel left/center/right: same tested mapping, no strain. Check both LED pairs
   still work when steering is active.
2. Left paddle (5): red + yellow blink. Right paddle (4): white + blue blink.
   Turn past the selected-side threshold and return: that signal cancels.
3. Motor teammate tests quarter/half/full throttle on the raised-wheel bench.
   Live firmware targets approximately 75/150/300 RPM. Use USB `diag` for
   target and actual milli-RPM; divide by 1000 to get RPM.
4. At speed, brake: motor mode=2; physical wheels stop in braking mode.
   Hold throttle and brake together: brake must win.
5. While motor, steering and blinkers run together, observe resets, stalls,
   encoder faults or supply problems. Record observations; don't infer timing
   from how quickly the GUI refreshes.

## 9. Run fault and recovery checks

Use the [measurement worksheet](doc/PART4_MEASUREMENTS.csv).

| Action | Expected result | Recovery |
| --- | --- | --- |
| Single A press | SELF_TEST (state 6), all hazards, dynamic motor brake, servo OFF | Release throttle; double-press A within 400 ms; then center wheel and explicitly arm/live servo |
| Remove only Pi TX -> STM RX wire | Within checkoff limit: ERROR_TIMEOUT, dynamic brake, hazards, servo OFF | Keep GND connected; reconnect signal with throttle released; verify LINK_OK; arm/live again |
| Press Nucleo B1 | Latched ERROR_MOTOR, enables off/coast, hazards, servo OFF | Stop proxy/bridge before reset; reset Nucleo, then repeat startup/load/arm/live |
| Stop Pi bridge (Ctrl+C) | No new UART commands; timeout/brake/hazards | Restart bridge; release throttle before recovery; re-arm servo |
| Close servo console | Servo PWM expires within its 500 ms lease | Motors are independent; reopening does not auto-arm servo |

To demonstrate rejected input, first release throttle, issue servo `off`,
and stop the live bridge. In the Pi terminal run each test separately:

```bash
python3 part2_bridge.py --mode bad-range
```

Expect `ERROR_BAD_INPUT` (3), hazards, brake; stop it with Ctrl+C. Then:

```bash
python3 part2_bridge.py --mode bad-crc
```

Expect the same safe behavior. Ctrl+C, restart the live command from step 6,
center the wheel and re-arm servo. Do not run these concurrently with live mode.

## 10. Measure timing and finish the record

Use [PART4_TIMING](doc/PART4_TIMING.md), not GUI/console timestamps, for physical
deadlines. Save throttle, brake, steering, blink frequency/duty/front-rear skew,
self-test, link-loss and status-period captures. Run normal logging and every
implemented subsystem while measuring. Recheck after the real ADC backend is added.

In a fourth PowerShell window, after stopping a log-producing run:

```powershell
$repoPath = 'C:\Users\hetia\CMU\18649\18649_team4_integration'
$piAddress = Read-Host 'Pi address'
New-Item -ItemType Directory -Force "$repoPath\logs\part4\pi" | Out-Null
scp "labuser@${piAddress}:18649/part2/logs/part4*.csv" "$repoPath\logs\part4\pi\"
Get-ChildItem "$repoPath\logs\part4\pi"
```

Choose one returned filename, then summarize its software telemetry:

```powershell
$statusCsv = Read-Host 'Full path of the CSV to summarize'
& 'C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts\python.exe' "$repoPath\tools\summarize_status.py" $statusCsv
```

This reports sequence gaps/current validity and MCU timestamp intervals.
It **does not** certify physical response deadlines.

Update the measured-result column in PART4_TASK_TABLE and the measurement CSV
only with real results. Keep filenames and screenshots. The `logs/` directory
is Git-ignored; save important captures to your shared evidence location
deliberately. No measurement has been invented or pre-filled.

## If something fails

- **No STM status:** check final board flashed, PA9/D8 -> Pi RX pin 10, GND,
  serial device, and no other process holding the port.
- **No LINK_OK:** check proxy target IP, wheel connect, UDP8000 and Pi TX ->
  PA10/D2. Keep the Pi terminal's exact error text.
- **SERVO ERR on live:** check `load`/valid calibration, use `arm` before
  `live`, center the wheel, require LINK_OK and clear self-test/faults.
- **ERROR_MOTOR:** capture `diag`. Fault 1 is latched B1; 2 is encoder/GPIO;
  3 is PID data; negative numbers are HAL errors. Correct the cause before reset.
- **ERROR_ACTUATOR or trace_errors nonzero:** save the USB log; inspect the
  corresponding output/pin configuration. Marker errors invalidate timing data.
- **UNAVAILABLE currents:** expected until 3.5 is implemented/calibrated.
- **Deadline missed:** save the waveform and exact firmware/log; don't mark
  PASS because it looked responsive. The next software change should address
  the measured cause.

## Completion checklist

- [ ] Current motor teammate's changes are included.
- [ ] All actuators run on one final Nucleo with verified final wiring/power.
- [ ] Combined normal operation, brake override, A self-test and recovery pass.
- [ ] Cold start, UART loss and invalid input pass.
- [ ] Current sensors are physically calibrated and reporting (3.5).
- [ ] Required scope captures meet the deadlines under simultaneous load.
- [ ] Actual task table, measurement evidence and team values are updated.
- [ ] Team can explain ISR/thread/work/timer roles and synchronization.

The USB-dependent servo recovery remains a documented bench policy. Confirm
with the TA whether checkoff requires automatic steering recovery after link
restoration; that behavior is not silently enabled here.
