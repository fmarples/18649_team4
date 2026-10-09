# Part 4 probe board and timing measurements

The handout requires these **13 separate breadboard rows, in this order**.
Build this with power off. These are additional high-impedance measurement taps,
not replacements for the wires driving motors, servo and LEDs. One signal per
five-hole row; opposite sides of a breadboard center gap are not connected.

| Row | Tape label | Connect this signal to that row |
| --- | --- | --- |
| 1 | GND | Common Pi/STM32/driver signal ground |
| 2 | GND | Same common ground; extra probe-ground location |
| 3 | UDP_RX | Pi 4 **physical pin 11**, BCM17 |
| 4 | CMD_TX | Pi 4 **physical pin 13**, BCM27 |
| 5 | CMD_RX | STM32 **PC2, Morpho CN7 pin 35** |
| 6 | PWM_SET | STM32 **PC3, Morpho CN7 pin 37** |
| 7 | PWM_OUT | Left motor ENA control signal, STM32 **PB4/D5** |
| 8 | DIR_A | Left motor **IN2** control signal, STM32 **PA6/D12** |
| 9 | SRV | Servo signal, STM32 **PB9/D14** |
| 10 | FL | Front-left LED signal, STM32 **PB6/D10** |
| 11 | FR | Front-right LED signal, STM32 **PA5/D13** |
| 12 | RL | Rear-left LED signal, STM32 **PA4/A2** |
| 13 | RR | Rear-right LED signal, STM32 **PB8/D15** |

**Why IN2 for DIR_A:** the confirmed left-forward polarity is IN1=0, IN2=1;
dynamic braking makes both zero. IN2 therefore has the falling edge needed to
time a forward-to-brake transition. Left IN1 stays low and would not show it.
These are **3.3 V logic/control signals**. Do not connect a logic analyzer to
L298N OUT1/OUT2, motor terminals, or the 12 V supply. Probe ground goes to common
GND, never to a switched motor output.

PC2/PC3 are newly allocated measurement outputs in this branch, not previously
confirmed wiring. Check nobody used them for another function. They are on
the long Morpho header, not the Arduino D/A sockets. Read the CN7 labels and
pin-1 marking before counting; pins 35 and 37 are adjacent on the odd-numbered
row at the end opposite pin 1. Confirm against ST's F401RE diagram; do not use
a guessed left/right orientation or a board with another model number.

Sources: [ST UM1724, NUCLEO-F401RE connector tables](https://www.st.com/resource/en/user_manual/dm00105823-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf),
[Raspberry Pi GPIO documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio).
On the Pi, `pinout` also displays physical header numbering.

## What each software edge means

- UDP_RX toggles after userspace `recvfrom` returns each UDP datagram, even one
  later rejected or discarded. It does not timestamp radio/NIC arrival.
- CMD_TX toggles immediately **before** a UART write, including refresh and
  stop frames. It includes OS buffering delay; it is not the actual TX wire.
- CMD_RX toggles in the UART ISR when the last byte of a correctly framed
  28-byte candidate arrives, **before queueing and CRC/range validation**.
  Invalid CRC/range candidates also get a marker. Header junk does not.
- PWM_SET toggles just after the final commanded **left** motor timer write
  succeeds. It excludes the temporary zero-PWM writes used during direction
  changes. The right timer is written next. There is no marker when no output
  update was required. It is not evidence the physical PWM waveform changed.

Both rising and falling edges are events. Do not divide the spacing between
same-direction marker edges by assumptions about the packet rate. An unchanged
refresh command may have CMD_RX without a PWM_SET. Associate a measurement with
the command that actually changed the requested output, not an unrelated PID
update. Decode the Pi TX/STM RX wire on an extra analyzer channel when available.
28 bytes at 115200 8N1 take about **2.43 ms** on the wire; the handout's local
2 ms response starts at command completion, so do not include the entire frame
and then mislabel it as local processing latency.

STM32 markers are enabled by `CONFIG_LAB_TIMING_GPIO=y`; `diag` must show
`trace_errors=0`. Pi markers require the bridge's `--trace-gpio` option.
They use [libgpiod v2 output requests](https://libgpiod.readthedocs.io/en/v2.3/python_misc.html).
Before using them, run on the Pi:

```bash
sudo apt update
sudo apt install -y python3-serial python3-libgpiod gpiod
gpioinfo -c /dev/gpiochip0 17 27
```

Verify this is the Pi 4's GPIO controller and these offsets are GPIO17/GPIO27,
unused by other software. If a different chip contains them, pass its path as
`--gpiochip`. Do not force-release someone else's GPIO request. The no-marker
bridge works without libgpiod, but cannot supply these two test points.
Initial setup/cleanup drives markers low; ignore those edges in captures.

## Capture procedure (repeat with all normal subsystems running)

1. Have one person operate controls and another handle the scope. Secure the
   raised-wheel bench. Keep the servo console and Pi logging open.
2. Connect the instrument ground to row 1; connect channel 1 to the start
   signal and channel 2 to the end signal in the table below. Select 3.3 V
   logic thresholds if using an analyzer. Use at least 1 MS/s for millisecond
   response checks, and a finer setting for front/rear skew if available.
3. Make a deliberate control change. Capture enough before/after it to identify
   the relevant command. Save the actual waveform/CSV and a screenshot showing
   cursor positions and units. Repeat several times, not just the fastest case.
4. Enter worst observed/min/max values and capture filenames in
   `PART4_MEASUREMENTS.csv`. Keep blanks for unmeasured results. Repeat while
   turning, blinking, sampling (once available), reporting and logging together.

| Test | Start / reference | End / quantity | Target and interpretation |
| --- | --- | --- | --- |
| Throttle software response | CMD_RX for changed throttle | Corresponding PWM_SET edge | <=2 ms; includes queue, CRC, scheduling and output API |
| Actual motor PWM change | PWM_SET | First waveform period at new duty on PWM_OUT | Record separately; scope verifies timer-output behavior |
| Brake response | CMD_RX for brake command | DIR_A falling edge while previously forward | <=2 ms; then verify ENA high and equal INs for dynamic brake |
| Steering | CMD_RX for changed steer | First SRV pulse reflecting new width | <=50 ms; physical wheel motion is a separate observation |
| Turn signal response | CMD_RX for paddle press | First selected lamp edge | <=100 ms |
| Normal blinker | One lamp over >=10 cycles | Frequency, duty, drift | 0.9..1.1 Hz; nominal 50% duty; record measured duty |
| Front/rear synchronization | FL vs RL, then FR vs RR | Paired edge skew | <=1 ms |
| Hazards | All four lamp signals | Frequency and synchronous operation | Nominal 2 Hz, 50% duty |
| A self-test | UDP_RX for the accepted first A press (correlate with decoded wheel packet); no corresponding CMD_TX/CMD_RX should follow | Brake DIR_A edge and hazard output | Pi stops commands; existing 60 ms MCU timeout targets checkoff's <=100 ms, not the conflicting <=10 ms requirement |
| UART link loss | Last CMD_RX before unplugging signal | Brake edge and first hazard state | <=100 ms checkoff; 60 ms software timeout + processing |
| Status heartbeat | STM TX D8/PA9 (additional probe) | Start-to-start of decoded 56-byte frames | 18..22 ms; each frame takes about 4.86 ms wire time |

For A self-test, capture UDP_RX together with the Pi TX wire/CMD_TX and actuator
outputs. A is consumed on the Pi, so measuring from an A-bearing CMD_RX is no
longer valid. Verify command silence through button release, pedal changes and
upstream UDP loss, then double press to recover. Bytes queued before the latch
may still reach the MCU; its 60 ms timeout is measured from the last accepted
command, not directly from the wheel press. Status traffic in the opposite
UART direction should continue. The user confirmed this timing policy for
[issue #2](https://github.com/fmarples/18649_team4/issues/2); no physical result
is claimed by the software tests.

For link-loss testing, remove only Pi TX -> STM RX; keep GND and power in place.
Reconnect with throttle released. Fault hazard phase may already be high when
the error occurs; choose a repeat that reveals entry or correlate state/other
outputs rather than treating the next falling edge as entry time.

The bridge CSV and `tools/summarize_status.py` report MCU frame-construction
timestamp intervals, sequence gaps and validity. They cannot prove physical
wire timing, a 2 ms brake response, or a waveform's duty cycle. Pi-side markers
also add userspace GPIO-call overhead; report measurements with instrumentation
enabled and describe their reference points.
