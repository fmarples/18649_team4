# Prototype operating review — October 29

The required-scope design is ready for the course's final **prototype fabrication
review**. We recommend keeping the present CAD for that review. This is not an
unconditional electrical qualification or authorization to place an order.
The remaining pre-fabrication action is the team/TA review of the submitted
design, including the limitations below. The course deadline is now
[October 31 at 10 p.m.](https://18449-f26.slack.com/archives/C0BRYGTD4HH/p1793301588360959),
with staff checking boards before the fabrication batch.

## Intended load and Pi supply

We use a bare Raspberry Pi 4 running the car software, without a powered USB
accessory, camera, display or fan. We budget **1.5 A for the Pi plus 0.3 A for
other 5 V loads**. This is a design assumption, not a measured maximum or a
software-enforced limit. Raspberry Pi's published workload example reaches
1.25 A; the additional 20% is our planning allowance. Its recommended 3 A
supply capacity is not a statement that a bare Pi continuously consumes 3 A.
See the [official power documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply).

We retain the existing 3.3 A rail allocation as a stress reference; we have not
reduced the regulator rating or concealed its earlier results. Sustained 3 A
Pi optimization is deferred. At actual bring-up, a workload that exceeds the
planning allowance or produces undervoltage requires reassessment before use.

The updated copper mesh varies only the Pi load and keeps the other modeled
loads fixed. At 1.5 A, positive-feed loss is **35.596 mV** at 20 °C. The table
adds an assumed 80 °C copper temperature, 20 mV return allowance and the stated
contact/lead resistance, with seven ground contacts sharing equally.

| Pi current | 10 mΩ per contact/lead allowance | 20 mΩ allowance |
| --- | ---: | ---: |
| 1.5 A planning | 4.9335 V | 4.9164 V |
| 2.0 A higher-load sensitivity | 4.9144 V | 4.8916 V |
| 3.0 A deferred sustained stress | 4.8763 V | 4.8420 V |

These values precede startup and load-step transients. The 4.8615 V upper
undervoltage-detector corner is a comparison, not a minimum operating-voltage
specification. The 1.5 A case leaves 55–72 mV to that comparison; this is useful
static margin, not a promise that every transient fits within it. Source
tolerance, copper, contacts and returns are separated rather than treating
the nominal 5.1 V setting as the voltage at the Pi.

## Input paths, heat and protection

The shared-input model uses 80% converter efficiency, local input-voltage
iteration, hot copper, a 20 mΩ FET assumption, two fuses at twice their typical
cold resistance, and a 30 mΩ harness/contact/return allowance.

| Pack voltage | Planning input current | Simultaneous higher-load sensitivity |
| --- | ---: | ---: |
| 10.5 V | 2.496 A | 6.490 A |
| 11.1 V | 2.394 A | 6.203 A |
| 12.6 V | 2.185 A | 5.633 A |

Planning loads are 0.72 A aggregate motor supply, 0.39 A average servo, 1.8 A
on 5.1 V and 0.8 A logic. The higher case uses 2 A aggregate motor supply,
3 A servo and 2.3 A on 5.1 V. It is **not a continuous operating rating** or a
permitted stall. Calculated local converter inputs stay above 9.46 V in these
cases. PWM, actual motor loading and transients can change the result.

The pre-FET input path has at least 2.5 mm outer copper. Parts of the shared
protected trunk are 1.2 mm, with layer changes. The
[TI/IPC-2221 approximation](https://www.ti.com/lit/an/snva766/snva766.pdf)
gives about 8 °C steady rise for an isolated 1.2 mm/35 µm trace at the
2.50 A planning current, but about 72 °C at 6.49 A. It is an empirical trace
screen, not a board or via temperature prediction. The route-tree model
can assign a parallel-via group to one predecessor; it does not establish
individual barrel currents. Sustained high aggregate current is therefore
outside the supported planning case. Adding a continuous 6–10 A capability
would require a deliberate copper/thermal redesign, not just a larger fuse.

At 1.8 A output, the Pi buck's modeled conduction plus switching-overlap
loss is 0.245–0.521 W across the stated assumptions. The largest case needs
an effective thermal resistance below about 163 °C/W at 40 °C ambient,
before unmodeled losses. The logic example is 0.169 W at 0.8 A. These are
loss sensitivities, not guaranteed junction temperatures; TI's reference-board
thermal resistance cannot be substituted for our board's value.

For the assumed 90% at 0.1 A / 10% at 3 A servo duty, average current is
0.39 A but RMS current is **0.953 A**. Heating depends on RMS current, so
squaring the 0.39 A average would understate it. The high-state regulator
loss example is 1.194 W while active; its 10% contribution is 0.119 W,
excluding light-load losses and unknown pulse duration. We do not support
holding the servo stalled continuously. The capacitor/inductor and feedback
checks in [Capacitor-bank-review.md](Capacitor-bank-review.md) remain applicable.
The [TPS564252 datasheet](https://www.ti.com/lit/ds/symlink/tps564252.pdf)
supports the regulator model; startup and thermal behavior still need bench
validation after assembly.

The removable 10 A blade remains a **candidate for the main input harness**.
Its published opening curve does not establish protection of every PCB branch,
an L298 bridge or a sustained overload of the narrow trunk. Final installed
fuse selection must match the assembled harness and observed startup/operating
envelope before LiPo power. This selection does not change the holder footprint.
If the required operating envelope exceeds the above planning case, stop and
reopen the layout review. Keep the [fuse review](Fuse-and-scope-review.md) visible
to the TA; it has not been silently marked qualified.

## Checks that follow fabrication

These are required before the relevant use, not optional work and not
measurements required from an unbuilt board:

1. Before assembly/order: confirm actual stock shortfalls, servo harness method,
   and solder process. Keep the Samtec socket out of SMT reflow; accommodate the
   inductor paste recommendation without flooding fine-pitch ICs.
2. Before first power: inspect polarity and soldering; check for shorts; verify
   harness continuity, socket alignment (Pi pins 3–38), retention and mechanical
   clearances. Start from a current-limited bench supply with actuators disabled.
3. Commission unloaded rails, then logic/Pi and actuators in stages. Record Pi
   boot/car-software voltage and current, rail overshoot/ripple and temperatures.
   Do not infer a successful startup from the DC calculation or increase a
   supply limit merely to conceal a fault.
4. Before LiPo driving: integrate and test Front PA3 sampling, status transport,
   Rear enable gating and the latched battery guard. Test missing/stale status
   and reset behavior. Confirm the fuse/harness decision and disconnect the
   pack after cutoff; the guard does not disconnect all electronics.

Deferred optional work: sustained 3 A Pi qualification, added peripherals,
extra hardware motor limiting, deliberate stall characterization, a 2 oz
copper redesign, and obtaining a proprietary simulation tool solely to extend
stress analysis. None is claimed complete or needed for the selected course
prototype scope. Bench startup and thermal checks above are not optional.

## Reproducible evidence

- [Pi-operating-mesh-check.json](Pi-operating-mesh-check.json): saved-board
  0.05 mm DC mesh at 1.5 A; other loads unchanged.
- [Prototype-power-check.json](Prototype-power-check.json): input, voltage,
  loss and empirical trace sensitivities, with assumptions and source hashes.
- [check_prototype_power.py](check_prototype_power.py): reproduces the planning
  calculations using KiCad Python; it does not edit the PCB.
- [Fabrication-check.json](Fabrication-check.json): unchanged CAD hash, zero
  native ERC/DRC/parity/unconnected findings. Manufacturing checks establish
  file consistency; they do not constitute powered verification.

The matching CAD SHA-256 is
`65c7e6d7c2cad47429379644d5696d946711c12c861110e707f4e2eccd0d90d0`.
