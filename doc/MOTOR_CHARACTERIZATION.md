# Motor startup and holding measurements

## Use the simultaneous results

On 2026-09-27 the user changed the test requirement from separate motors to
**both motors driving forward together**, because that is the operating case.
The user confirmed raised wheels, 10 kHz PWM, 200 ms kicks, up to 4-second holds,
and the existing per-wheel motion guards. Units remain wheel RPM and ms/s.

The user also requested a one-command automated sweep and explicitly authorized
checked reflashing after expected no-progress faults. This supersedes the earlier
manual-only sequencing. Failed duties are not automatically retried. Reverse,
encoder, HAL or reset errors abort the batch. No software fault-clear command or
weaker guard was introduced.

These measurements use the same shared **12 V / 2 A supply**, L298N, wiring and
forward polarities documented in [HARDWARE.md](HARDWARE.md) and
[STM32_PINOUT.md](STM32_PINOUT.md). Wheels were unloaded and raised. No current,
temperature, rail transients or PWM waveform measurements were made.

## Simultaneous startup

Each test starts both wheels from rest with the same duty, without a preceding
kick. Maximum powered time is 200 ms. Either wheel failing to advance four raw
counts within 150 ms stops both and latches its fault.

| Duty | Batch result |
|---|---|
| 60% | Both started, 1/1 |
| 55% | Both started, 3/3 |
| 50% | Neither established forward rotation, 0/1; left no-progress fault 1 stopped both |

**55% is the lowest tested simultaneous startup duty.** The observed transition
is above 50% and at or below 55%; 51–54% are untested. At 50%, the captured counts
moved only 1–3 counts before cutoff and returned to zero. Two preceding manual
simultaneous checks at 60% and 55% also passed, but are not included in batch counts.

Use **60% / 200 ms as a provisional startup kick** to leave margin. Three starts
are not a reliability qualification, and raised-wheel results do not prove loaded
startup or electrical safety.

## Simultaneous holding and speed

Every trial starts both motors with 60% for 200 ms, then switches both to the
listed duty for at most 4 seconds. The same no-progress/reversal guards remain
active across the transition; it does not reset their progress timers.

| Holding duty | Left RPM | Right RPM | Mean RPM | Result |
|---|---:|---:|---:|---|
| 55% | 92.9 | 100.1 | 96.5 | Completed 4 seconds, 1/1 |
| 50% | 64.5 | 74.0 | 69.3 | Completed 4 seconds, 1/1 |
| 45% | 40.7 | 47.6 | 44.1 | Completed 4 seconds, 1/1 |
| 40% | 19.3 | 26.7 | 23.0 | Completed 4 seconds, 3/3; speeds averaged over these three trials |
| 35% | Not a sustained-speed result | Not a sustained-speed result | Not applicable | Left stalled about 2.6 seconds into holding; fault 1 stopped both |

At 40%, individual final-window speeds were LEFT 19.7, 19.8 and 18.5 RPM,
RIGHT 25.9, 27.3 and 26.8 RPM. Both remained forward throughout each completed
hold. Some deceleration remained, especially on the left: first-half to second-half
late-window speed fell by roughly 4–10%. Do not extrapolate this to indefinite
operation or label it an exact steady-state speed.

**40% is the lowest tested duty that kept both motors moving through all three
4-second holds.** 35% failed the joint operating requirement; the cutoff prevents
inferring whether the right motor alone could have continued. 36–39% are untested.
For initial low-speed closed-loop work, 45% has more observed holding margin than
40%, but it is a starting point for testing, not a guaranteed operating floor.
No throttle-to-target-speed mapping or velocity controller was implemented here.

### How speed was measured

The encoder reader timestamps the two raw counts using MCU uptime in milliseconds
under the encoder lock. The control thread publishes a coherent `SAMPLE` record
with applied duties, phase, stage, counts and fault. The console transmits these
at about 20 Hz without blocking the higher-priority cutoff loop.

Only samples in the final approximately one second of the powered HOLD stage are
used, after three seconds of settling for the 4-second trials. Actual windows in
the batch were 952–955 ms. Kick and coast-down samples are excluded. The encoder
sample immediately precedes output updates within the control iteration, so a
stage-boundary sample is not a scope measurement of the switching instant; late
windows are well away from that boundary.

`RPM = forward_count_delta * 60000 / (1320 * elapsed_ms)`

Negate LEFT raw deltas and retain RIGHT raw deltas, then average the two wheel
speeds. The provisional **1320 x4 counts/wheel revolution** comes from
[ENCODER_SPEC.md](ENCODER_SPEC.md), not the conflicting vendor count of 3960.
Host USB timestamps are diagnostic only and do not enter the speed calculation.

JSON also records peripheral m/s using the reported 75 mm wheel diameter. That
is not measured vehicle ground speed. The `settled_in_late_window` flag only checks
whether the two half-window RPM estimates differ by at most 10% or 1 RPM; it does
not establish steady state, thermal stability or long-term holding ability.

## Evidence and final state

The complete one-command run is:

`logs/motor-bench/sweep-20260927-044102/summary.json`

Its status is `COMPLETE`. It contains all 12 trial results and absolute paths to
the raw captures. The directory also holds each build/test log, flash capture,
preflight rest check and final stop verification. Relevant raw captures:

- Startup: `startup-both-60-20260927-044127.json`;
  `startup-both-55-20260927-044156.json`, `044255.json`, `044302.json` with the same
  prefix; failed `startup-both-50-20260927-044226.json`.
- Holding: `hold-both-55-20260927-044331.json`,
  `hold-both-50-20260927-044406.json`, `hold-both-45-20260927-044440.json`,
  `hold-both-40-20260927-044514.json`, `hold-both-35-20260927-044548.json`,
  and the two 40% confirmations ending `044622.json` and `044632.json`.

All captures are under ignored `logs/motor-bench/`, not committed evidence files.
Each completed trial ended with disabled outputs and stationary encoders. No
invalid transitions, GPIO errors, unexpected resets or reversal faults occurred
in this simultaneous batch. The two expected failures latched fault 1; the runner
verified rest before the user-authorized reflash.

The final image restores **startup 60% / 200 ms; holding 60% / 200 ms then 55% /
4000 ms**. The final reflash was idle-checked only. Final telemetry reported
IDLE, stage OFF, both duties zero, both encoder counts zero, no fault/errors.
The app is still the independent bench diagnostic, not the Part 2 link app.

## Earlier single-wheel investigation, not the operating-case table

Separate 4-second holds produced these final-window RPM estimates:

| Duty | Left | Right |
|---|---:|---:|
| 55% | 92.2 | 102.0 |
| 50% | 65.7 | 72.0 |
| 45% | 40.4 | 46.7 |
| 40% | 17.7 | 24.6 |

Initial 2-second tests overestimated some low-duty late speeds because the wheel
was still slowing. LEFT at 35% moved for two seconds but failed the longer test.
The first 4-second attempt tripped the reverse guard after a small backward count
change near rest, `hold-left-35-20260927-041433.json` and matching `.crash.txt`.
The user explicitly requested one repeat and watched it slow smoothly to a stop.
That repeat latched no-progress fault 1 after about 2.4 seconds,
`hold-left-35-20260927-041946.json`. Guards were not relaxed. RIGHT at 35% was not
tested separately. Later tests proceeded at 40% with the user's confirmation.

These are diagnostic history. Use the simultaneous table above for the requested
both-motors operating case, and do not pool separate-wheel trials into its repeat
counts. Wiring, current limits, loaded operation and long-term behavior still
require independent validation.
