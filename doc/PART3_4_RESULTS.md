# Part 3.4 evidence record

**Latest user confirmation:** after the integration-branch merge, Tianyi reported
Part 3.4 tested. Treat the separate blinker subsystem as functionally tested;
the earlier pending-test statements below are historical. No new scope captures
were provided. Combined self-test motor braking and response timing still need
the final motor Nucleo, rather than the separate LED board.

Date: 2026-09-26. Board: Tianyi's separate NUCLEO-F401RE LED bench.

## Handout correction after the initial visual test

The initial image below omitted startup hazards and the single/double-press
self-test. These were real gaps, corrected after rereading the checkoff:
startup/no link now selects hazards; G920 A (button 0) latches self-test on
the first press and a double press within 400 ms clears that latch. Real link
errors still override the clear. Motor braking remains an integration task.

The corrected firmware builds (34,416 bytes flash, 9,600 bytes RAM).
All 20 C tests pass in QEMU (12 blinkers + 8 self-test), and all 7 Python
protocol tests pass. These changes have not yet been physically demonstrated
by the user. The older startup-OFF capture below describes the original image,
not the intended behavior of the correction. A later steering bench image
will also include this correction. Timing measurements remain pending.

Update: the combined `lab2-tianyi-steering` image was subsequently flashed and
verified on this same board. Its boot console confirms startup HAZARD mode;
see `PART3_3_RESULTS.md`. A physical A-button single/double test and motor
braking verification are still pending.

## User reports

- All four LEDs connected: red front-left D10, yellow rear-left A2,
  white front-right D13, blue rear-right D15; 470-ohm resistors to GND.
- Pi UART and Logitech wheel available; ST-LINK USB now attached to Windows.
- No scope or logic analyzer currently available.
- After running the tests, Tianyi reported that the LEDs continue blinking
  after the Python script exits and that steering alone does not activate
  blinkers. Both were explained as intended: command loss selects hazards;
  paddles activate a turn signal and steering return cancels it.
- Tianyi then reported that everything else works. Record this as a general
  user-reported visual result, not an instrument measurement or an independent
  per-case capture. No firmware change was needed for those two observations.
- The selected-signal cancellation sequence was explained. A separate explicit
  observation of crossing and returning through each raw steering threshold
  was not supplied; do not infer measured threshold accuracy from the general
  report.

## Automated preparation

- Windows detected ST-LINK COM11, serial `066BFF485270535067124020`.
- Pre-flash serial read showed existing Part 2 firmware in WAITING.
- Existing protocol tests: 6 passed. Windows launcher test: 1 passed.
- New Pi visual-sequence script passes Python syntax compilation.
- NUCLEO-F401RE firmware built with this host's Zephyr
  `v4.4.0-16655-g7a7003dec4b9` and SDK 1.0.1: 34,056 bytes flash, 9,600 bytes RAM.
- **12 actual C core tests passed in QEMU**: phase boundaries/no drift, switching,
  cancellation/hysteresis, held/opposing buttons, fault priority/recovery,
  waiting and long uptime. Git's mingw64 runtime DLL directory was added only
  to the test process PATH to start QEMU; no global environment change.
- Final image programmed using ST-LINK with explicit adapter serial selection;
  OpenOCD reported **Verified OK**, then reset the target. Reduced reset debug
  speed to 100 kHz after earlier default-speed reset/poll errors.
- Post-flash COM11 capture shows the new firmware running in
  `STM WAITING ... blink=OFF L=0 R=0`. No GPIO initialization error observed.
- Image SHA-256:
  `0927e79d7f3379b59e02abaf270674896ca647087573a454b9176c419c4ae973`.
- Two pre-flash 512 KiB firmware reads were saved locally with matching SHA-256
  `bedff2d7db371daa9909abf872dd23758e56367d5fa7dbE5c90dda02ba8d0327`.
  Earlier debug/reset warnings are why these are retained as backups rather
  than described as a tested restore procedure.
- Local raw logs/backups are under `logs/part3_4/` (Git-ignored), including
  `core-tests.txt`, `flash-final.txt`, and `post-flash-console.txt`.
- Automated SSH reached the Pi at 172.26.166.33 but login requires interactive
  authentication. No files were copied to the Pi by the agent.

## Physical checklist and measurement status

The general visual-success report above applies to the remaining observed
behavior. The table distinguishes that report from individually documented
results; it does not claim instrument validation or final integrated checkoff.

| Check | Expected | Actual observation/measurement |
| --- | --- | --- |
| Neutral valid link | Four external LEDs off | General visual-success report; no individual capture |
| Left paddle | Red + yellow only | General visual-success report; no individual capture |
| Right paddle | White + blue only | General visual-success report; no individual capture |
| Opposite selection | Previous side cancels immediately | General visual-success report; latency unmeasured |
| Same paddle again | Selected side cancels | General visual-success report; no individual capture |
| Steering alone | Does not activate turn signals | User explicitly reported this behavior |
| Self-cancel left/right | Beyond +/-8000, return inside +/-6000 | Procedure explained; no separate threshold-crossing result supplied |
| Held paddle | No repeated toggle or re-arm | No individual hardware result supplied |
| Both new presses in same command | Both sides off; otherwise newest wins | No individual hardware result supplied |
| Link timeout | All four hazards, 2 Hz | User reports continued blinking after script exits; rate unmeasured |
| Recovery | Hazards stop; old request not restored | General visual-success report; no individual capture |
| Normal frequency/duty | 1 Hz +/-10%, 50% duty | Instrument unavailable |
| Hazard frequency/duty | 2 Hz, 50% duty design | Instrument unavailable |
| Front/rear skew | <=1 ms | Instrument unavailable |
| Command-to-output response | <=100 ms | Instrument unavailable |
| Timing under complete system workload | Same limits with motor/ADC tasks | Integration pending |

Console `L/R` values are requested outputs, not measured pin voltages. QEMU
tests exercise the actual C state machine, not real GPIO or UART electrical
behavior. Keep screenshots/captures with this record when obtained.
