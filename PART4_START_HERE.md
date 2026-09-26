# Part 4 integration plan

Part 4 runs on the STM32. It combines the Part 3 components under Zephyr's
scheduler. The existing Part 2 Pi bridge remains the command source.

This is a work plan, not new firmware. The task table is a proposal. Part 4
is finished only after the real Part 3 drivers run together and their timing
has been measured on the board.

## 1. Use the agreed integration starting point

The team agreed to keep `pi/` and `stm32_zephyr/` at the repository root.
These contain Tianyi's Part 2 link implementation, not the older full-control
starter. Keep the Pi and STM32 on the matching CRC-based protocol in
[PROTOCOL.md](PROTOCOL.md). Do not restore the incompatible old protocol from
Git history during driver integration.

Tianyi's Part 4 responsibilities are scheduling, shared state, safety integration,
status reporting, and the task table. Confirm the Part 3 branch and driver
interfaces before combining firmware; relocation alone does not integrate that
work. The independent encoder diagnostic is in `bringup/encoder_test/`.
Read [the pin map](doc/STM32_PINOUT.md) for confirmed wiring and proposals.
Keep USART1 PA10/D2 and PA9/D8 for the Pi link and PA2/PA3 for the ST-LINK console.

## 2. Identify the responsibilities

Your teammate supplies working drivers and calibration: motor PWM and
direction, actual dynamic-braking operation, both encoder readings, steering
servo, four lamps, and three current sensors. Request the function names,
argument units, return values, and whether each call can wait/block.

You arrange when those functions run, how commands and measurements are
shared, which work takes priority, when the vehicle enters/leaves error, and
what the Pi receives in the status frame. Agree who owns PID and blinker
logic so neither person duplicates them.

Only one firmware image runs on the shared Nucleo. Coordinate flashing with
the person using it for Part 3.

## 3. Review the existing Part 2 program

Open `stm32_zephyr/src/main.c`. Search these names:

| Name | What it currently does |
| --- | --- |
| rx_callback | Collects UART bytes and queues candidate frames in an interrupt |
| accept_candidate | Checks a frame and updates accepted command values |
| set_error | Sets safe internal values; it does not brake a real motor |
| status_thread | Sends status to the Pi when the 20 ms timer signals it |
| console_thread | Prints diagnostic information at a lower priority |
| state_mutex | Protects the shared command/state structure |

Follow the data path: wheel -> Windows proxy -> Pi bridge -> UART queue ->
accepted STM32 command -> future driver calls -> current measurements/status
back to the Pi.

## 4. Prepare the task table

Open [PART4_TASK_TABLE.md](PART4_TASK_TABLE.md), the single task-planning table,
and review the proposed responsibilities with your teammate. A period says how
often work runs. A response deadline says how quickly its effect must happen. A priority decides which ready thread runs
first. A short period alone does not prove that a deadline is met.

The table already has the handout targets and a proposed schedule. Adjust it
when the real drivers are available. Leave measured results unfilled until
you have measurements.

## 5. Agree on driver interfaces

Before integration, fill in the following from your teammate's actual code:

| Capability | Information needed |
| --- | --- |
| Motor command | Function name, units/range, direction meaning, worst-case call duration |
| Dynamic brake | Function name and verified H-bridge pin state |
| Encoders | Functions for left/right counts or velocity, units and direction convention |
| Servo | Function name, pulse-width units and calibrated safe endpoints |
| Lamps | Function name and mapping of front/rear left/right outputs |
| Current sensors | Function name, mA conversion, valid/error indication, sampling duration |

Do not treat unavailable current data as measured zero. Assign one owner to
each actuator output; a motor control update must not overwrite a newer
brake/error decision. Keep shared-state locks short and release them before
UART transmission, ADC waits, logging, or slow driver calls.

## 6. Integrate after agreeing on the interfaces

Connect the actual driver functions to the proposed tasks. Use queues or
short mutex-protected snapshots to move state between threads. Keep interrupt
handlers bounded: capture bytes/counts and signal a thread, with no blocking
calls, logging, or heap allocation. Timer callbacks should signal the work.

On boot, link loss, invalid input, or a self-test fault, implement real motor
braking and hazard outputs. The existing Part 2 LED and internal values are
only communication indicators. Self-test must remain active until its
specified recovery gesture; a normal incoming wheel packet must not clear
that fault. Reconnection recovery must use fresh valid commands.

Update the status frame with the agreed vehicle state and three calibrated
current readings. If the packet definition changes, update both Pi and STM32
together and document it in PROTOCOL.md.

## 7. Finish together on the hardware

Once drivers are integrated, measure command-to-output response with scope
or logic-analyzer test points, and measure status and blink periods. Record
actual results in the task table. Console prints alone cannot prove 2 ms
response. Perform the final combined cold-start, brake override, self-test,
link-loss, invalid-input, and recovery demonstrations with your teammate.

The handout has conflicting numbers: self-test is 10 ms in its requirements
table and 100 ms in checkoff; cable loss is 150 ms in Part 2 and 100 ms in
checkoff. Plan for the stricter figures and ask the TA to clarify them.
Current STM32 link timeout is configured at 80 ms. A lost wheel UDP stream
currently adds up to roughly 100 ms on the Pi before UART commands stop;
review that complete path before enabling actuators.
