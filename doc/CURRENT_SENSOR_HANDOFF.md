# Part 3.5 handoff into Part 4

User confirmation: current sensors are unfinished. The prepared interface
reports all three channels unavailable. It does not enable ADC or change motor
behavior. The known family is ACS712; exact range/sensitivity and conditioning
are unconfirmed. Do not select a conversion factor from a similar-looking board.

The current work item runs on its own preemptible priority-3 workqueue, nominally
every 20 ms. It calls `current_backend_read()` in
`stm32_zephyr/src/current_backend.c`. Replace that one backend after Part 3.5:

```c
int current_backend_read(int32_t ma[3], uint32_t *valid_mask);
```

| Item | Contract |
| --- | --- |
| Channel order | 0 left motor, 1 right motor, 2 servo |
| Output unit | Signed integer milliamps, not volts or raw ADC codes |
| Validity | Bit i set only when ma[i] is physically acquired and calibrated |
| Missing channel | Clear its bit and use INT32_MIN |
| Legitimate zero | 0 mA with its validity bit set is a real zero measurement |
| Return | 0 for successful acquisition (possibly only some channels); negative errno for a failed acquisition |
| Error | All channel validity clears for that acquisition |
| Slow/hung backend | Status thread never waits for ADC; cached data expires at 100 ms |
| Motor policy | Read-only: no motor trips or current thresholds in this lab |

Sampling starts after app initialization. The sample timestamp is taken before
acquisition, so acquisition/filter time counts toward sample age. A mutex
protects cache copies only; do not hold it during ADC waits. Missed work slots
are skipped. `CONFIG_LAB_CURRENT_SAMPLE_MS=20` and
`CONFIG_LAB_CURRENT_MAX_AGE_MS=100` are initial scheduling/telemetry choices,
not measured sensor properties. Change them with documented reasoning if the
real driver requires it. Avoid busy loops and logging in the acquisition path.

Before enabling the real backend, provide:

1. Actual chip suffix/range and each board's wiring/supply.
2. Verified ADC-safe output conditioning: a 5 V sensor output must not directly
   overdrive a 3.3 V analog input. Record divider/amplifier ratio if used.
3. ADC reference, resolution and channels. Planned inputs are PA0/A0,
   PA1/A1 and PB0/A3; inspect the final board before connecting them.
4. Per-channel zero-current offset and sensitivity, with units; include the
   conditioning gain in the conversion. Do not manufacture these constants.
5. Filtering choice, acquisition duration and measured noise with motors on.
6. Recorded rest/free-spin/brief-stall readings required by 3.5, under the
   handout's short-stall procedure. This interface is not current limiting.

For a linear sensor, after measured ADC and conditioning conversion:
`current_mA = (sensor_output_mV - zero_offset_mV) * 1000 / sensitivity_mV_per_A`.
The actual constants, polarity and rounding must be validated on the bench.
Enable ADC devicetree/Kconfig only when those details are ready. The Pi bridge
already displays valid numeric readings and preserves them in its CSV; packet
layout and CRC need no changes. Stale age is reflected by the validity mask,
not a new timestamp field in the existing 56-byte frame.
