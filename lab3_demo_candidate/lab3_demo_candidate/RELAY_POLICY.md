# Immediate N2 relay

In scenario (c), N1 loses B and N3 loses A. N2 forwards valid foreign frames
between the surviving links without waiting for heartbeat failure detection.
The 60 ms heartbeat timeout still controls health monitoring; it no longer
decides whether a message can be forwarded.

## Receive and forwarding rules

- Only N2 relays. N1 and N3 consume messages without forwarding them. This covers
  scenario (c) and its A/B-reversed equivalent, not fault pairs requiring N1 or N3
  to act as a bridge.
- Validate the standard data frame, DLC and CRC before admission. Reject an
  out-of-range CTRL locally before putting it on the relay queue.
- Keep the original CAN ID, four-bit sequence and payload. FAULT identity also
  includes its source zone because that ID has several senders.
- Track multiple recent identities, not only the latest sequence for an ID.
  Suppress a repeated identity on either bus, including a direct and relayed copy
  received on the same bus. Record per-bus heartbeats before duplicate filtering.
- N2 queues the first valid foreign copy immediately. Its priority-2 worker checks
  whether the opposite-bus copy was already received, then claims at most one
  forwarding attempt onto that bus. There is no timer or heartbeat prerequisite.
- A 32-entry history expires after 5 ms from each identity's first arrival.
  Duplicates do not extend expiry. Live records are never evicted to admit new
  traffic. A queued frame whose history has expired is dropped and counted.
- Relay transmission uses a completion callback and `K_NO_WAIT` mailbox admission.
  It does not wait for an ACK. The driver still performs SPI work and can contend
  for locks. Submission/completion failures are counted and are not retried by
  the application for that identity; normal CAN controller retransmission is
  separate. A full transmit mailbox therefore remains a delivery failure.

The Pi's two notifiers now share one serialized Receiver and one expiring history.
Previously they had separate sequence dictionaries, which could not filter copies
across interfaces. Expiry also avoids permanently suppressing a same-sequence
first message after a reboot.

## Timing assumptions and observability

The 5 ms lifetime is inherited from the candidate's existing skew allowance,
not a measured bound and not a forwarding wait. It must cover actual native and
relay copy delay while staying below sequence reuse time (320 ms for a 20 ms
stream). A reboot inside the window can still reuse an indistinguishable identity.
Delayed duplicates beyond the window can be accepted again. Measure this bound
and enforce the catalog's source traffic limits before claiming correctness under
load. This is a single-relay design, not a general loop-free multi-relay protocol.

`RELAY_TX` (PC6) toggles before a forwarding submission. `OBS_MAX_US relay` measures
history lookup and submission, including interruptions/waits inside that interval;
it excludes time queued before the worker starts and subsequent wire completion.
The `relay` diagnostic counts successful TX callbacks. The extra `RELAY` line
reports `tx_error`, `stale`, and the pending `queue_overflow` flag. That flag is
consumed by the supervisor and is not a cumulative counter.

Immediate forwarding may add copies on a healthy bus. Recalculate bus load and
node interference. Dispatch remains priority 1 (and contains STEER/DRIVE); RELAY
remains priority 2. This patch removes the heartbeat gate but does not prove the
2 ms end-to-end deadline. Shared SPI blocking, queueing and arbitration still
belong in the response-time analysis. Other ordinary transmitters retain their
existing synchronous send path.

## Software verification

The C regression executable links the production `frame_history.c`. It checks
immediate first-message forwarding without any heartbeat input, both directions,
duplicate suppression on either bus, interleaved sequences, independent FAULT
sources, 4-bit wrap, reboot/expiry, 32-bit uptime wrap, stale queue entries, full
history and bounded attempts after a failed submission. It passed 104 checks.

The Python suite passed 19 tests, including shared Receiver behavior, late FAULT
duplicates after a clear, heartbeat timestamps on both interfaces, and malformed
frame rejection. A real python-can 4.6.1 virtual-bus test exposed the original
non-callable Receiver; the callback and listener-list registration are corrected.
Run from this candidate directory:

```sh
python -m unittest discover -s pi -p 'test_*.py' -v
cc -std=c11 -Wall -Wextra -Werror -I stm32_zephyr/src tests/test_frame_history.c stm32_zephyr/src/frame_history.c -o test_frame_history
./test_frame_history
```

On Windows, the same C sources were compiled with MSVC `/std:c11 /W4 /WX`.
Build compatibility fixes use `CONFIG_WATCHDOG` for Zephyr 4.3 and guard the
optional manual recovery API by configuration and advertised driver capability.
These fixes do not implement or verify MCP2515 bus-off recovery.

Both NUCLEO-F401RE profiles built successfully on 2026-10-18 with Zephyr 4.3.0
and Zephyr SDK 0.17.4. N2 used 48,072 bytes flash / 24,256 bytes RAM; N3 used
47,036 bytes flash / 22,080 bytes RAM. These builds were not flashed.

## Remaining hardware verification

The changed Pi program and both changed Nucleo images must be tested together.
Do not mix the immediate relay with an old receiver that admits same-bus copies.
Keep the existing Part 3 measurement build as its own baseline.

1. Confirm each logical message is applied once with both buses healthy, including
   when a native second copy arrives after N2 has already forwarded the first.
2. Capture the **first** CTRL after N1-B and N3-A are disconnected, as well as later
   messages. Verify delivery without a 60 ms startup gap; scope N1 input to N3
   output to evaluate the actual 2 ms deadline.
3. Repeat with A/B exchanged and verify HB_N3 reaches N1 through N2 in reverse.
4. Check failures and recovery with a full TX mailbox, an unacknowledged bus and
   reconnects. Inspect `tx_error`, `stale`, queue flags, bus error counters and logs.
5. Measure maximum duplicate skew and relay queue delay under expected load, then
   complete node, bus and end-to-end timing tables. No hardware pass is claimed.
