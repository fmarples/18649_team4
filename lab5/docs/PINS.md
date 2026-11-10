# Lab 5 pin additions

These are **implemented allocations**, not confirmation that the bench is wired. Keep the [working Lab 3 pinout](../../doc/LAB3_PINOUT.md) and its SPI erratum: XIAO D9 is MISO and D10 is MOSI. Do not remap existing control or CAN pins for this lab.

| Signal | Pi BCM | Pi physical pin | N2 and N3 MCU pin | Meaning |
|---|---:|---:|---|---|
| PPS | 16 | 36 | PA8 | Rising edge at computed global whole second; nominal 1 ms pulse |
| LEADER | 20 | 38 | PA9 | This node is the current local Raft leader |
| SYNC | 21 | 40 | PB7 | Leader, or follower with a recent accepted REF |
| REF_RX | 26 | 37 | PC10 | Toggles on an accepted (not duplicate) REF |

All are 3.3 V signals. Use the board's documented header mapping for the named MCU pins; connect common signal ground and scope inputs appropriately. Existing B1 is PC13, so PA8 is free in the current Lab 3 application. USART1 and I2C3 remain disabled to free PA9/PA8. These allocations do not claim compatibility with a different PCB or optional Pi accessory.

The recorded bus mapping is Pi can0 = logical A, can1 = logical B, N2 with `swap_ab.conf`, N3 without it. Verify the labels once at the bench before interpreting link-fault results. The compiled allocation is authoritative in `stm32_zephyr/boards/nucleo_f401re.overlay` and `pi/cockpit5.py`.

## Existing blinkers and status LEDs

These assignments are unchanged from the Lab 3 demo. They were cross-checked
against the [submitted Lab 3 wiring diagram](https://drive.google.com/file/d/1YJkmi71ZOdM8uiPj8Twf8HzoyBWe7e__/view)
and both generated Lab 5 device trees on November 10.

| Node | Left blinker | Right blinker | Error indicator |
|---|---|---|---|
| N2 / front | PA4 / A2, probe row 10 | PB8 / D15, row 11 | PC0 / A5, row 13 |
| N3 / rear | PC4, probe row 12 | PC5, row 13 | PC0 / A5, separate extra connection |

**Probe row 13 has different meanings on N2 and N3.** Identify the board and
GPIO before calling an LED an error indicator. PB0/PB1 are bus-degraded status
outputs, and CAN_RX/CAN_TX markers indicate traffic; none is a vehicle blinker.
ST-LINK ending `124020` runs N2/front, and `171333` runs N3/rear in this session.

Lab 5 calculates hazard phase from global time. With the Pi application absent,
the intended hazard rate is 4 Hz; with the Pi present but cockpit error persisting,
it is 2 Hz. ERR is a separate state indication and stays high during a sustained
error. Do not restore the historical Lab 2 front-blinker pins: PB6 and PA5 are
now used by CAN/SPI. Register sampling and visual agreement are recorded in the
[bring-up record](BRINGUP_2026-11-10.md); scope timing is still unmeasured.
