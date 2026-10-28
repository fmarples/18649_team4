# Battery guard module

This is standalone logic for the selected standard 3S LiPo. It is **not yet
part of the Front/Rear application** and has not stopped a physical motor.
The circuit and design assumptions are in [Battery-LiPo.md](../Battery-LiPo.md).

The module starts disarmed. A fresh, valid sample of at least 11.1 V permits
an explicit arm request. A sample at or below 10.5 V, an invalid/over-range
sample, or more than 100 ms without a sample latches the fault. Voltage
recovery cannot clear it. These thresholds are design choices, not measured
cell protection. A total-pack reading cannot identify an imbalanced low cell.

## Host check

With a C11 compiler, from this directory:

```sh
cc -std=c11 -Wall -Wextra -Werror battery_guard.c test_battery_guard.c -o battery_guard_test
./battery_guard_test
```

The first command builds the logic and its test without MCU peripherals;
the second exercises startup, cutoff boundaries, stale/invalid data, fault
latching, timer wrap and ADC conversion. The expected result is one PASS
line. This tests decisions made from supplied readings, not the ADC, CAN,
motor wiring or power electronics. MSVC C11 /W4 /WX tests and a Cortex-M4
freestanding ARM GCC compilation passed for this revision.

## Integration still required before LiPo operation

1. Configure Front PA3 as ADC1_IN3, with no pulls, calibrated VDDA and the
   acquisition/settling conditions in the circuit note. Sample at 100 Hz.
   Reject readings while ADC calibration, supply or acquisition is invalid.
2. Feed readings and a monotonic millisecond clock into the guard. Preserve
   the Lab 3 PA0/PA1 timing markers and existing CAN assignments. Define the
   battery-status message in the shared application catalog before coding it;
   this module does not allocate a CAN identifier.
3. At Rear, gate every L298-enable/PWM update with fresh valid battery status
   and the latched state. Missing messages and MCU startup must leave both
   enables low. A repeated old reading is not proof of a fresh ADC sample.
4. Test the integrated fault paths with simulated readings/current-limited
   bench power before connecting the pack. Confirm that neither stale CAN
   status nor a later motion command can re-enable the motors after cutoff.

Serialize calls or provide synchronization if multiple tasks use one guard.
`battery_guard_init` clears its state and must not be called automatically
after a trip. Motor stop leaves other electronics powered; disconnect the
pack promptly. This module is not a BMS or autonomous battery disconnect.
