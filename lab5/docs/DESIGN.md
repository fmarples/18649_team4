# Protocol and engineering boundaries

## Consensus and client state

Three fixed voters have IDs N1/cockpit=1, N2/front=2, N3/rear=3. Two votes/replicas form a majority. Operational `NODE_*_DOWN` does not change the voting membership. `l5_addNode`, `l5_dropNode`, `l5_addLink`, `l5_dropLink`, and `l5_getNetwork` implement the client API. Only committed entries change the graph. Requests to a follower are redirected; state changes and source-sequenced EVENT retries are idempotent.

The Raft core persists term/vote and each new entry before replying. A new leader appends a no-op barrier. It never commits an older-term entry solely by counting replicas; committing a current-term entry commits its preceding prefix. Pre-vote avoids term inflation by isolated followers. The implementation stops rather than wrapping its 16-bit term or overflowing the 30,000-entry log.

`MEMBER` is the checkoff label for the detailed COCKPIT/NODE/CANLINK state entries. Codes 21–23 are `EVENT_N1`, `EVENT_N2`, `EVENT_N3`; a shell/signal action generates one. These diagnostic events have an implicit per-origin sequence, not an arbitrary user payload. This interpretation connects the body's event list to the checkoff's otherwise undefined MEMBER/EVENT labels.

## CAN catalog additions

| Standard ID | Contents / cadence |
|---|---|
| `0x081..0x083` | REF from N1..N3; leader only, 20 ms |
| `0x111..0x113` | Direct HELLO from N1..N3; 20 ms, never forwarded |
| `0x400 + (source << 4) + (destination << 2) + fragment` | Four-fragment RPC; source 1..3, destination 0=broadcast or 1..3, fragment 0..3 |

REF bytes: cycle uint8, term uint16 little-endian, global microseconds low uint32 little-endian, CRC-8. REPORT includes a coarse 48-bit clock epoch (upper 32 bits in 65,536 µs units) to recover a cold follower after the REF low word wraps. It also carries direct-bus observations, upstream state and the leader's held-event count.

RPC serialization is 24 bytes, versioned in `l5_encode/l5_decode`; each CAN fragment holds an 8-bit sequence, six payload bytes and CRC-8. Reassembly is bounded, duplicate-aware and checks the complete RPC CRC. Existing Lab 3 CTRL, BLINK, HB, FAULT and FORCE layouts remain unchanged. Empty APPEND cadence is 100 ms; nonempty/commit traffic is sent when needed. REF is an election heartbeat, not a log replication ACK.

Direct presence expires at 60 ms; REPORT liveness at 66 ms allows one report interval/processing margin. A missing direct origin enables repair forwarding after 40 ms, before the earliest 60 ms election timeout. The committed graph selects a bridge; fresh direct observations provide a bootstrap fallback when the graph itself needs repair. The relay cache suppresses loops. The simulator covers the specified N1-off-B/N3-off-A topology and an STM32 leader failure.

## Persistent memory

F401RE flash `0x08000000..0x0803ffff` is firmware (256 KiB maximum). Sectors 6 and 7, `0x08040000..0x0807ffff`, form two 128 KiB log banks. Each bank contains a header, term/vote journal and 30,000 four-byte term/event/CRC records. Bank activation is written last. Interrupted compaction leaves the previous bank readable. An invalid active record fails closed and requires diagnosis; tests do not claim word programming is physically atomic under power loss.

The Pi uses a file-backed equivalent of the journal, syncing writes before acknowledgments. A separate SQLite display ledger has a unique Raft-index key. Catch-up replays state, but already recorded display entries are not duplicated. A process crash between durable display insertion and console printing can omit a terminal line; the durable display history remains the source for checking exactly-once records. Restart does not clear either state file.

## Time

We use an affine raw-to-global map and the `(leader delta)/(follower raw delta)` frequency ratio. Later phase corrections are capped at 50 µs and global reads are monotonic. Initial synchronization may step; it is not a leader-handover measurement. New leaders preserve their synchronized clock. Nucleo CLOCK_REALTIME is updated on accepted references while raw cycle time stays independent.

The 240 µs transfer delay is a planning value, **not measured**. Software RX queue residence, MCU REF TX queue residence and time spent in the Pi tick before sending REF are compensated. A Nucleo leader stamps its REF at enqueue time after any durable work. Controller arbitration, SPI/interrupt latency, SD/flash stalls and Linux scheduling still require observation. PPS/blink tasks sample global time every 200 µs. Consequently a 50 µs algorithmic correction does **not** prove a ≤100 µs physical edge disturbance.

## Release boundary

This is an offline-checked implementation for bench bring-up, not a completed checkoff. In particular:

- F401 single-bank flash programming/erase can stall execution. A conflicting suffix or exhausted term journal triggers bank compaction; its worst-case duration/watchdog effect is unmeasured. Do not claim the <1 s election or phase limits during compaction from these host tests.
- Pi durable Raft writes are synchronous for consensus safety. Disk latency can delay its control loop; measure REF/PPS under live workload before accepting it. The display logger and optional network mirror are asynchronous, but that does not make Raft persistence asynchronous.
- Debug/console queues are bounded and report drops; the console is not authoritative if output is lost. Dump the committed log while idle. No network-delivery guarantee exists after a queue overflow.
- The report body broadly describes node failure; checkoff step 8 explicitly requires no error solely on an STM32-leader failure with a healthy cockpit. We implement the explicit checkoff behavior. Local isolation/test faults and missing/stale cockpit still enter error.
- Cold/restart semantics, real LED/GPIO timing, bus labels, task stack high-water marks and failure/brake response need the bench evidence in `CHECKOFF.md`.

Sources: [Lab 5 handout](https://drive.google.com/file/d/1t1by1C3fa68qGf46RoKFRM3L3FZnoXNS/view), [Raft extended paper](https://raft.github.io/raft.pdf), [Zephyr flash-area API](https://docs.zephyrproject.org/latest/services/storage/flash_map/flash_map.html). Firmware is built against Zephyr 4.3.0, not assumed to match the latest documentation automatically.
