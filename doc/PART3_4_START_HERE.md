# Part 3.4: Tianyi's separate blinker bench

This branch adds blinkers to the existing root-level `stm32_zephyr` UART app.
It has no motor, steering-servo, encoder or current-sensor drivers. The motor
bench and the teammate's checkout are untouched. The final lab still combines
the subsystems on one MCU. Do not describe this as completed integrated testing.

**Correction after reviewing the full checkoff:** startup now flashes hazards;
G920 A/button 0 single-press latches self-test hazards. Double-press A within
400 ms to clear the manual latch (link must also be healthy). The old image
started with LEDs off and lacked this button. Those were incomplete behaviors,
not the final lab requirement. Physical motor braking still requires integration.

## Confirmed bench wiring

User reports all four LEDs connected on a separate NUCLEO-F401RE:

| LED | Position | Header | MCU GPIO |
| --- | --- | --- | --- |
| Red | Front-left | D10 | PB6 |
| Yellow | Rear-left | A2 | PA4 |
| White | Front-right | D13 | PA5 |
| Blue | Rear-right | D15 | PB8 |

Each channel uses a 470-ohm series resistor to GND. GPIO connects to the LED
anode; cathode connects through the resistor to GND. Thus HIGH means on.
LED orientation and physical light output still need the user's visual check.
PA5 also drives the board's green user LED, which follows the right pair.
The former link-status LED code has been removed. The overlay frees PB8 from
I2C1, PB6/PA5 from SPI1, and PA5 from the board-default PWM configuration.

The motor board's E5V power arrangement is documented separately in HARDWARE.md;
do not assume this separate LED board was rewired the same way. Keep its working
power setup and shared Pi/STM ground. Never connect the two boards' power rails.

## Start each session

Firmware only needs flashing when it changes. Power the Pi and LED board,
connect their existing UART wiring, and attach the wheel to Windows with G HUB.

1. Open **Windows Command Prompt** and connect to the Pi:

   ```bat
   ssh labuser@172.26.166.33
   ```

   Use its current address if that has changed. This is the registered address
   previously supplied by Tianyi; it was reachable during preparation, but SSH
   automation could not log in without interactive authentication.

2. In the **Pi SSH window**, start the already-installed bridge:

   ```sh
   cd ~/18649/part2
   python3 part2_bridge.py --mode live
   ```

   Only one process may own `/dev/serial0`; stop an older bridge/test first.
   Older bridge text says LINK-ONLY/no actuators because it predates this image;
   the UART packet format is unchanged and the new image drives only blinkers.

3. In a **second Windows Command Prompt**, start the existing wheel proxy:

   ```bat
   "C:\Users\hetia\CMU\18649\18649_team4_blinkers\windows\start_wheel_proxy.cmd"
   ```

   Enter the current Pi address without `/17`, then click **connect** in the
   course GUI. Leave force feedback off. Keep the wheel secured and hands clear
   while connecting, since the course program can give a short bump.

4. Optional: open the STM32 USB console in another Windows Command Prompt:

   ```bat
   "C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts\python.exe" -m serial.tools.miniterm COM11 115200
   ```

   COM11 was identified on this host for the separate board; it can change.
   Exit miniterm with Ctrl+]. Console lines contain `blink=OFF/LEFT/RIGHT/HAZARD`
   and the requested GPIO levels `L=0/1 R=0/1`. These are software state, not
   independent measurements of light, voltage, period or response latency.

## Visual checklist with the real wheel

Start with the steering wheel centered and both paddles released.

1. With `LINK_OK` and no request, all four external LEDs should be off.
2. Tap the **left paddle** (raw button 5). Red and yellow blink together:
   about half a second on, half a second off. White/blue remain off.
3. Tap the **right paddle** (button 4). Left stops; white/blue start together.
4. Tap that same right paddle again: right cancels. Holding a paddle does not
   repeatedly toggle or restart the signal.
5. Select left. Turn left until console `steer` is **-8000 or lower**. Return
   toward center to **-6000 or higher**: left cancels automatically.
6. Select right. Turn right to **8000 or higher**, then return to **6000 or
   lower**: right cancels. Center is approximately zero.
7. Select right and turn past 8000, then release it and select left while still
   turned right: left remains selected; the previous right-turn history must
   not cancel it. A subsequent left turn and return cancels it normally.
8. The newest paddle press wins even if the other remains held. If both new
   presses arrive in exactly the same command, both sides cancel; this exact
   case is included in the automatic test below. Neither case selects hazards.
9. In the Pi bridge window press **Ctrl+C**. After command timeout all four
   flash together twice per second (250 ms on, 250 ms off).
10. Restart the same live bridge command. With the wheel proxy still sending,
    `LINK_OK` returns and hazards stop. Old turn selections do not resume.
    Release any held paddles and press one again to request a new turn.
11. With LINK_OK, tap **A** once: all four hazards start immediately and remain
    on after release, despite valid incoming wheel packets. Status is SELF_TEST.
12. **Double-tap A** (two distinct presses within 400 ms): hazards clear if the
    link is healthy. Holding A is one press, not a double press. A real link fault
    cannot be cleared with this button. Existing turns are not restored.

Before the first valid command after boot the LEDs flash hazards (WAITING).
Timeout, rejected complete input and UART queue overflow activate hazards.
The self-test button is now implemented, but physical motor braking is absent.
During integration the same fault predicate must override motor propulsion and
command verified dynamic braking. A single press is processed immediately; the
firmware does not wait 400 ms before entering failure. A release must be seen
for at least 20 ms before another press is accepted. The handout lists 10 ms
local response in its table and 100 ms at checkoff; neither has been measured.

## Optional automatic visual sequence from the Pi

This avoids depending on wheel buttons while verifying LED wiring and UART.
Stop the live Pi bridge first with Ctrl+C. On Windows, copy two files:

```bat
scp "C:\Users\hetia\CMU\18649\18649_team4_blinkers\pi\blinker_check.py" "C:\Users\hetia\CMU\18649\18649_team4_blinkers\pi\part2_protocol.py" labuser@172.26.166.33:~/18649/part2/
```

Then, in the Pi SSH window:

```sh
cd ~/18649/part2
python3 blinker_check.py
```

Watch the announced colors and actions. The script checks UART replies, but
cannot see the LEDs. On exit it stops commands, so hazards resume until the
live bridge starts. Run it only on this LED bench, not the motor integration.

## Design and integration contract

- Pure C state machine: `blinker_core.c/.h`. GPIO adapter: `blinker_gpio.c/.h`.
- One main-thread owner (priority 1) validates UART input, enforces the 80 ms
  link timeout, steps the blink state and writes outputs. Other threads only
  read the mutex-protected published snapshot. No blink globals are shared
  unsafely with a timer callback.
- Main normally wakes within approximately 1 ms. Absolute monotonic 64-bit
  elapsed time determines phase; late iterations do not accumulate drift.
  Normal period is 1000 ms, hazard period 500 ms, both 50% duty.
- A new side or hazard starts ON immediately. Switching sides clears previous
  turn history. Same-side fresh press cancels. Two new opposing presses in one
  command cancel; otherwise the newest press wins even if the other stays held.
  Holding a button never re-arms a self-cancelled turn.
- Turn thresholds are team choices, not handout constants: +/-8000 raw counts
  (roughly 24% of the measured half-range) arms return cancellation; returning
  inside +/-6000 cancels. The 2000-count hysteresis avoids flicker near one
  boundary. Units are raw G920 counts, not servo degrees. Adjust after testing.
- Four GPIO writes are grouped without thread preemption; interrupts stay
  enabled. Front/rear <=1 ms skew and response <=100 ms must be measured.
- `self_test_fault(..., link_ok)` is true on startup, link failure, or a latched
  A-button self-test. It is the shared predicate to connect to motor braking.
  `blinker_step(... ready, fault, buttons, steer)` accepts the integrated
  vehicle error flag in place of this app's link-error flag. Fault overrides
  buttons. First healthy input after a fault clears hazards and consumes held
  buttons so an old request is not restored.
- Keep PA5 owned by the blinker, not another heartbeat task. When merging
  motor PWM, remap TIM2 to PB10 before re-enabling pwm2 (default PA5 conflicts).
  Continue USART1 remapping to PA9/PA10; PB6 belongs to front-left.
- The existing UART command/status layout is unchanged. Current readings
  remain unavailable. Status 5 = SELF_TEST was added; update Pi
  `part2_protocol.py` with the SCP command above so it prints that name rather
  than UNKNOWN. Other link errors take precedence. Status does not report blink phase.

## Build and test on Tianyi's Windows host

PowerShell, using this host's existing environment (not the other teammate's
`C:\Users\13982` paths):

```powershell
$env:Path = 'C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts;C:\Program Files\Git\mingw64\bin;' + $env:Path
$env:ZEPHYR_SDK_INSTALL_DIR = 'C:\Users\hetia\zephyr-sdk-1.0.1'
Set-Location 'C:\Users\hetia\CMU\18649\zephyrproject\zephyr'
west build -b nucleo_f401re/stm32f401xe -d 'C:\Users\hetia\CMU\18649\18649_team4_blinkers\build\blinkers' 'C:\Users\hetia\CMU\18649\18649_team4_blinkers\stm32_zephyr'
west build -b qemu_cortex_m3 -d 'C:\Users\hetia\CMU\18649\18649_team4_blinkers\build\blinker-tests' 'C:\Users\hetia\CMU\18649\18649_team4_blinkers\tests\blinker_core'
west build -d 'C:\Users\hetia\CMU\18649\18649_team4_blinkers\build\blinker-tests' -t run
```

Git's mingw64 directory supplies QEMU runtime DLLs on this host; no global PATH
change is needed. After PROJECT EXECUTION SUCCESSFUL, exit QEMU with Ctrl+A,
then X if it stays running. Do not flash the QEMU test image. Actual hardware image is
`build/blinkers/zephyr/zephyr.bin`. Flash only the identified LED bench board.

## Remaining evidence

Keep software tests, physical visual observations and oscilloscope/logic
analyzer captures separate. No instrument is currently available. Later record
normal period/frequency and 50% duty across several cycles; hazard frequency;
front/rear skew <=1 ms; command-to-output <=100 ms; repeat under integrated
motor/control/ADC workload. Successful build or console timing is not that
physical evidence.
