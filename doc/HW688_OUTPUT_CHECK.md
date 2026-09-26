# Checking Tianyi's fixed-output HW-688

Photo identification, 2026-09-26: `PXL_20260926_224629914.jpg` shows the
component side; `PXL_20260926_224634357.jpg` shows VIN+, VIN-, 5V and GND on
the underside. No adjustment potentiometer is present. This is a fixed
nominal 5 V USB buck board, not the adjustable converter previously assumed.
Its actual output and load capability remain unmeasured.

In the component-side photo, USB is at the top and the black barrel jack at
the bottom. The blue block beside the barrel jack is INPUT; the block beside
the USB socket is OUTPUT. Use the underside labels to identify the exact
positive/negative screw, since flipping the board changes apparent orientation.

| Printed label | Meaning | Connection for this unloaded test |
| --- | --- | --- |
| VIN+ | Input positive | Known lab 12 V adapter positive, through labeled DC breakout/splitter |
| VIN- | Input negative | Same adapter negative |
| 5V | Regulated output positive | Red multimeter probe |
| GND | Output negative | Black multimeter probe |

## Do this with the servo, STM32 and Pi disconnected from this second converter

1. Unplug the 12 V adapter from mains. Keep the already-working STM32 power
   arrangement unchanged; do not modify its converter while preparing this one.
2. Use the kit's DC barrel-to-screw adapter or a labeled 12 V distribution
   connection. Do not open the wall adapter or cut its mains cable. Connect
   adapter + to converter VIN+ and adapter - to VIN-. This procedure uses the
   converter's screw input; leave its barrel jack empty.
3. To attach a wire: loosen the terminal screw, insert about 5 mm of stripped
   conductor into the wire opening, tighten and gently tug. The screw head is
   for clamping; do not wrap bare wire around it. Avoid exposed copper bridging
   adjacent terminals. Mark positive and negative while reading the underside.
4. Place the module component-side up on dry cardboard so its underside cannot
   touch metal. Keep output terminals free of attached loads.
5. The photographed meter is **Extech MN35**. Its existing leads are correct:
   black in COM, red in V/ohm/mA/Temp; leave the 10A socket empty.
6. Turn the pointer to **20 V DC**, the 20V marking with a straight/dashed-line
   symbol. From OFF it is three detents counterclockwise: 600V DC, 200V DC,
   then 20V DC. Use the printed marking as the final check. Do not select
   resistance, current, or an AC/wavy-line range.
7. Plug in the 12 V adapter. Hold insulated probe handles. Touch black to the
   metal of the output GND terminal and red to the metal of output 5V. Each
   probe touches one terminal only; do not bridge adjacent screws.
8. Record the reading. Around 5 to 5.2 V is expected for this module family;
   this is not a measured team result. If the reading is negative, recheck probe
   polarity and labels. If it is close to 12 V, unplug and check that you measured
   the output rather than the input; do not connect a load.
9. Unplug the adapter, then remove the probes and switch the meter OFF.

There is no voltage adjustment screw. Do not try to change the output by
turning terminal screws. A successful 5 V measurement does not establish a
suitable supply for the listed LD-1501MG servo, specified at 6–8.4 V. Obtain
a suitable adjustable supply/converter or confirm an alternative with course
staff before servo calibration. Do not run ARM from this fixed 5 V supply.

Sources: user's three photos, the [Extech MN35 product specifications](https://www.flir.com/en-ca/products/mn35/),
an equivalent [module supplier's 5.2 V specification](https://www.jzk-jzk.com/collections/electronic-component/products/24v-12v-to-5v-5a-power-buck-module-dc-dc-step-down-power-supply-converter-with-led),
and [Hiwonder's chassis servo specifications](https://wiki.hiwonder.com/projects/Ackermann-Chassis/en/latest/docs/3_Arduino_Version_formatted.html).
