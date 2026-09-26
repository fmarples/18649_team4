LAB 2 UART STARTER PROJECT
==========================

This is a STARTER implementation for Part 2 of the drive-by-wire lab.

The lab handout requires:
- A command sent from the Pi for every UDP state update, no less often than every 50 ms.
- A status frame from the STM32 every 20 ms +/- 10%.
- The status frame includes the three current-sensor readings and zone state.
- The STM32 detects a lost link and enters fail-safe.
- Malformed/out-of-range commands are rejected.

The handout recommends UART, but it does NOT prescribe the byte-level UART
protocol. The protocol in this folder is therefore a team design choice.

FILES
-----

pi/
  main.c
      Receives UDP wheel packets and forwards each valid update over UART.

  udp_receiver.c/.h
      Receives the 276-byte wheel packet and extracts steering, throttle,
      brake, and the first 32 button indices.

  uart.c/.h
      Opens the Pi UART and sends the command frame.

  protocol.h
      Shared byte-level command/status frame definitions.

  Makefile
      Builds the Pi bridge.

stm32_zephyr/
  src/main.c
      Starts the UART link, checks for timeout, and sends a status frame
      every 20 ms. Hardware-control calls are TODO placeholders.

  src/uart_link.c/.h
      Zephyr UART parser, command validation, timeout tracking, and status
      frame transmission.

  src/protocol.h
      Same protocol definitions as the Pi.

  src/app_state.h
      Structures shared by the STM32 application.

  prj.conf
      Zephyr configuration.

  app.overlay
      BOARD-SPECIFIC TEMPLATE. You must configure the UART peripheral and
      pins for your actual STM32/Nucleo board.

WHAT TO EDIT BEFORE RUNNING
---------------------------

1. PI UART DEVICE
   Edit pi/main.c:

       const char *uart_device = "/dev/serial0";

   Verify which UART device is actually connected to the STM32.

2. PI UART CONFIGURATION
   The starter uses 115200 baud, 8 data bits, no parity, 1 stop bit (8N1).
   Both devices must use the same settings.

3. WHEEL PACKET OFFSETS
   Edit/check pi/udp_receiver.c.

   The handout says the packet is:
       4-byte little-endian counter
       272-byte DIJOYSTATE2

   The code uses standard DirectInput offsets for lX, lY, lRz, and
   rgbButtons. Verify these against the state.h supplied with the course
   proxy before relying on them.

4. RAW VS SCALED VALUES
   The starter transmits steering/throttle/brake as signed 16-bit values.

   The lab explicitly asks the team to decide whether to send raw wheel
   counts or scaled values. Decide this as a team and document it.

   If you choose normalized values, change both sides consistently.

5. BUTTON INDICES
   Part 1 of the lab asks you to record the actual raw button indices.
   The starter assumes button indices 0..31 and packs them into a uint32.

   Edit the button handling if your selected buttons are outside 0..31.

6. STM32 BOARD / UART PINS
   Edit stm32_zephyr/app.overlay.

   You need the exact board name and exact UART peripheral/pins.
   The file intentionally does not guess these.

7. STM32 UART API / ZEPHYR VERSION
   uart_link.c uses Zephyr's asynchronous UART API.

   Make sure CONFIG_UART_ASYNC_API is supported/enabled for your Zephyr
   version and board. If your board/driver only supports the interrupt-driven
   API, adapt uart_link.c accordingly.

8. COMMAND VALIDATION
   The current int16 range check is only a transport-level placeholder.
   Replace it with your team's actual valid steering/throttle/brake ranges.

   The lab requires bad/out-of-range commands to be rejected without
   actuating the vehicle.

9. FAIL-SAFE TIMEOUT
   The Part 2 text says 150 ms (three missed 50 ms updates).
   The checkoff says fail-safe within 100 ms.

   This starter uses 100 ms, the stricter checkoff target. If your course
   staff tells your team to use another value, change and document it.

10. ERROR STATE
    main.c contains placeholders for:
      - motor braking / PWM disable
      - steering safe state
      - 2 Hz / 50% hazard flashing
      - any other fail-safe outputs

    Replace these TODOs with your actual actuator functions.

11. CURRENT SENSORS
    status_thread currently sends zero for all three currents.
    Replace those assignments with your ADC/current-sensor functions.

12. CONTROL THREADS
    The UART callback only parses bytes and stores the newest valid command.
    Your actual motor, steering, brake, and blinker control should run in
    appropriate Zephyr threads/timers/work items.

13. PROTOCOL CHECKSUM
    The starter uses an 8-bit additive checksum. This is simple and easy
    to debug, but the team should understand its limitations. You may choose
    CRC instead; if you do, change both devices.

14. STATUS RX ON PI
    uart_receive_status() is included as a starting point, but it intentionally
    does not yet implement a complete byte-by-byte status parser. Add one
    before relying on the Pi's status data.

15. UART WIRING
    Pi GPIO UART is 3.3 V logic. Do NOT put 5 V on a Raspberry Pi GPIO pin.
    Connect TX to RX, RX to TX, and common GND. Verify the STM32 UART voltage
    levels before connecting.

BUILDING THE PI PROGRAM
-----------------------

On the Pi:

    cd pi
    make

Then run:

    ./pi_uart_bridge

Start the laptop wheel proxy so it sends UDP packets to the Pi on port 8000.

The Pi should print the decoded values and forward each valid UDP update.

STM32 BUILD
-----------

From a Zephyr environment, after editing app.overlay for your board:

    west build -b <YOUR_BOARD> stm32_zephyr
    west flash

Replace <YOUR_BOARD> with the exact Zephyr board target for your Nucleo.

RECOMMENDED BRING-UP ORDER
--------------------------

1. Run the provided wheel monitor on the Pi.
2. Confirm steering/throttle/brake/button values.
3. Test the Pi UART by sending a known test frame before connecting actuators.
4. Flash the STM32 with only UART parsing/status functionality.
5. Confirm a changing steering value reaches the STM32.
6. Test malformed frames and out-of-range values.
7. Unplug the Pi-to-STM32 cable and verify fail-safe timing.
8. Only after the communication layer is stable, connect the actuator-control
   code.
9. Add current-sensor readings and verify the 20 ms status heartbeat.
10. Add the full Zephyr scheduling/control structure.

IMPORTANT
---------

This code intentionally does not claim to implement the complete Lab 2 system.
It implements the UART/UDP communication skeleton so your team can integrate
the actual motors, encoders, brake, servo, blinkers, ADCs, and safety logic.

Keep the protocol definition in your team's design documentation because the
lab says the Pi-to-STM32 link is a rehearsal for the later CAN message catalog.
