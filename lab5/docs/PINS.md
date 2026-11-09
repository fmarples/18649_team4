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
