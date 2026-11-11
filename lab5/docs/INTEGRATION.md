# Integration review and capture interpretation

This is the technical record for the Lab 5 integration/routing work. The offline tests below use the production C core on a desktop. Subsequent flashing, three-node integration and partial physical fault checks are recorded separately in [the November 10 bring-up record](BRINGUP_2026-11-10.md); the full cases in [CHECKOFF.md](CHECKOFF.md) remain unfinished.

## Receive-to-commit path

1. The CAN callback queues a received frame. The dispatcher passes it to the Lab 5 agent, which validates framing/CRC and decides whether it needs forwarding. CRC detects corrupted bytes; it does not prove that a field such as a node number is valid. We added a 1–3 bounds check before the relay indexes its per-node tables using a FAULT reporter.
2. HELLO records direct physical presence on its received bus. HELLO is never forwarded. REPORT carries the observations to the leader. Seeing a frame, discovering a link and committing a link-state change are separate steps.
3. A complete RPC is reconstructed from four fragments and checked again. Follower client requests are redirected to the leader. The leader appends a proposed change, replicates it, then advances the commit index after a majority acknowledges it. Only committed entries change `getNetwork`.
4. The routing graph selects direct delivery or a bridge. A bounded discovery fallback repairs stale routes; duplicate suppression prevents loops. Existing CTRL/HB/BLINK/FAULT traffic can cross the bridge without changing its payload. REF forwarding compensates its timestamp, so REF payloads intentionally differ across hops.

For the required N1-off-B/N3-off-A case, N1 remains the leader and N2 is the bridge. N2's diagnostic request reaches N1 on A. N1's replication reaches N3 through N2 onto B. Being the bridge does not make N2 the leader.

## Offline coverage added

| Test | Assertions |
|---|---|
| 18 single-link cases: six links × three initial leaders | Same term/leader; all nodes remain present; exactly one DOWN and one UP entry per cut/restore; identical committed logs and correct link bits |
| 36 crossed-cut cases: six topologies × two cut orders × three leaders | All nodes stay reachable through the remaining bridge; no unnecessary election; one diagnostic event from each origin commits once; restoration converges |
| Six single links in the serialized-CAN model | Same graph/log invariants and bounded modeled queue; no reported host queue drops |
| Legacy traffic across the bridge | Unmodified CTRL/HB/BLINK/FAULT payload reaches the remote endpoint once; bad CRC is not forwarded; reverse heartbeat path works |
| Invalid FAULT origin | Values 0, 4, 127 and 255 cannot be used as relay-table indexes or forwarded as valid node identities |
| Saved-capture decoder | Production-generated fragments; healthy and bridged simulated traffic; separate buses; sequence wrap, duplicates, out-of-order fragments, timeouts, conflicting fragments, frame/RPC CRCs and identity mismatches |
| Saved-history comparison/export | Read-only SQLite snapshot, live WAL visibility, transaction isolation, ordered export, preservation of existing files, malformed entry rejection, missing versus conflicting history |

The 36 topology cases use a fixed receive-delay model. A separate model serializes CAN frames, but neither includes real SPI interrupts, flash stalls, Linux scheduling or electrical faults. Test-generated traffic is synthetic evidence only.

## Read a capture

On the Pi during a coordinated bench run, `candump -L any > captures/healthy-can.log` records classic-CAN frames in timestamped text. Stop that capture with Ctrl+C in its own terminal. Analyze a saved file on any machine with Python:

```sh
python lab5/tools/analyze.py candump captures/healthy-can.log --decoded-csv captures/healthy-decoded.csv
```

The command opens files only; it cannot transmit CAN. Inspect these outputs:

- `quality`: bad CRC, incomplete messages, unparsed lines and duplicates. An incomplete message can be a cut, recorder loss or simply the beginning/end of the capture. Investigate before interpreting a missing message.
- `ref_streams`: interval range and mean separately by bus, source and term; expected nominal cadence is 20 ms. Missing/duplicate cycle counters are also reported. A good average can hide a long gap: inspect the maximum and the raw timeline.
- `empty_append_streams`: interval range and mean for **empty** APPEND RPCs by bus, source, destination and term; nominal cadence is 100 ms. Entry-carrying APPENDs are excluded. A message is timed at its first observed fragment, not at an assumed leader transmission instant.
- `vote_requests_observed`: decoded REQ_VOTE count. Zero means none were decoded during this capture; it proves no election only in conjunction with adequate capture coverage and unchanged node terms/status. PREVOTE is counted separately.
- Decoded CSV: `source`, `destination`, `term`, `index`, `commit` and `event` let us trace a request and replication. Source is the logical origin encoded in the packet, not the physical relay transmitter. One event may have several packet observations because of two buses or retries; count committed entries, not APPEND packets, to check event uniqueness.

The Pi cannot see a segment through an unplugged local CAN interface. In the two-cut case, its capture cannot by itself establish receipt at N3. Save N3's serial log and committed network snapshot as endpoint evidence. Packet arrival timestamps also cannot establish LED phase or brake-response limits; those need the common-timebase scope recording.

## Compare committed histories

While idle, request `lab5 network` and `lab5 log` from both Nucleo consoles. Save the full output, not just the last few rows. Export the Pi's durable display history after its queue has drained:

```sh
python3 lab5/tools/export_ledger.py ~/.local/state/team4-lab5/display.sqlite captures/pi-history.jsonl
python3 lab5/tools/analyze.py logs captures/pi-history.jsonl captures/n2.txt captures/n3.txt
```

The first command reads a consistent SQLite transaction and creates a new JSONL file (one JSON object per line); it does not reset either persistent store. An in-memory queued entry is not yet in that snapshot. Copying only a running WAL database's main file can omit recent rows, so run the exporter on the Pi or use a proper SQLite backup.

Pi `STATUS` now includes `evidence`: CSV/console drop counts and the ledger's `durable_index`, queue depth, dropped rows and error. Before exporting, wait until `durable_index` catches up with `raft.commit`, the queue is empty, and errors/drops are absent. Queue depth alone is insufficient: a writer can have removed a row from the queue without finishing its disk commit. The durable index is updated only after the SQLite commit (and restored from the saved database at startup).

`durable_index` denotes the consecutive prefix starting at 1, not the largest
stored index. The host adapter retains up to the full 30000-entry log's
applied notifications; the Pi drains at most 64 per tick, limited further by
free ledger queue slots. This prevents a large restart replay from silently
losing its tail or flooding the asynchronous writer. A missing old SQLite row
can be filled by replay of the preserved Raft history; conflicting rows still
raise an error. Verify the repaired export rather than clearing either store.

`common_prefix_agrees` checks all indices up to the shortest captured history. `identical_complete_logs` additionally requires equal complete contents. `missing_indices` means the evidence lacks rows; `conflicts` means captured nodes disagree on an actual value at the same index. Preserve both histories when there is a conflict. Repeated identical console rows are deduplicated by comparison; exactly-once display and replay ordering still need their own test.

The MCU export takes a fixed committed-end snapshot and releases the protocol
mutex before each UART write. Check that its `LOG_BEGIN` and `LOG_END` indices
agree and that every index in that range was captured. A `LOG_ERROR` means the
export failed. Application diagnostics share the shell's output writer to
prevent character interleaving. The November 10 live check exported matching
complete 1844-entry histories from both Nucleos while the protocol continued;
the Pi comparison covers the previously saved prefix through 1801.

## Hardware boundary

The three nodes have joined using the existing Lab 3 bus mapping. Both Nucleos' A/B LED cut/restore subchecks passed. N2-led and Pi-led two-cut runs delivered EVENT_N2 to all three logs. With Pi leader in term 525 and graph `0x7/0x2d`, the capture shows N2's CLIENT request, Pi replication and N3's successful reply for entry 3418. Complete histories agree through 3566 after restoration. The operator confirmed steering/brake and left/right/cancel through the surviving route. The settled CAN interval contains no error heartbeats, but earlier transition errors include N3-only error reports consistent with a rear-only flash. This is not a fully clean fault-timing result. Remaining work includes input/transport fault diagnosis, scope limits and integrated failure/recovery rehearsal. Reported difficult jumper insertion explains why no additional repeat is requested solely for clean insertion; it does not establish the cause of every recorded outage. Compare all three histories again for later experiments. Save revision/configuration, bus mapping, cut/restore timestamps, CAN capture and all three node logs. Coordinate scope and persistence testing with the other roles. Passing host tests and these partial bench checks is not a completed TA checkoff.
