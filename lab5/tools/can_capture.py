"""Decode saved candump -L captures. Never opens a CAN interface.

The four-fragment format follows core/wire.c and core/lab5.c. Reassembly is
separate for each capture interface: fragments seen on different buses do not
prove that one receiver obtained a complete message. Counts are observations,
not proof of endpoint acceptance, commitment, or a completed hardware checkoff.
"""

from collections import Counter, defaultdict
import csv
from decimal import Decimal
from pathlib import Path
import re
import statistics

CATALOG = {
    0x010: "CTRL",
    0x020: "FAULT",
    0x100: "HB_N1",
    0x101: "HB_N2",
    0x102: "HB_N3",
    0x200: "BLINK",
    0x300: "FORCE",
}
RPC_NAMES = {
    1: "REQ_VOTE",
    2: "VOTE_REPLY",
    3: "APPEND",
    4: "APPEND_REPLY",
    5: "CLIENT",
    6: "REDIRECT",
    7: "REPORT",
    8: "REF_ACK",
    9: "PREVOTE",
    10: "PREVOTE_REPLY",
}
LINE = re.compile(
    r"^\s*\((\d+(?:\.\d+)?)\)\s+(\S+)\s+([0-9a-fA-F]+)#([0-9a-fA-F]*)\s*$"
)
CSV_FIELDS = (
    "timestamp_s",
    "first_fragment_s",
    "interface",
    "kind",
    "can_id",
    "source",
    "destination",
    "sequence",
    "term",
    "master_time_low_us",
    "prev_index",
    "prev_term",
    "commit",
    "index",
    "entry_term",
    "event",
    "success",
    "flags",
    "serial",
    "empty_append",
    "payload_hex",
)


def crc(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ (7 if value & 0x80 else 0)) & 0xFF
    return value


def decode_rpc(payload, src, dst):
    if (
        len(payload) != 24
        or payload[0] != 1
        or payload[1] not in RPC_NAMES
        or payload[2] != src
        or payload[3] != dst
        or crc(payload[:23]) != payload[23]
    ):
        raise ValueError("Invalid RPC version, identity, type or CRC")
    row = {"kind": RPC_NAMES[payload[1]], "source": src, "destination": dst}
    for offset, name in (
        (4, "term"),
        (6, "prev_index"),
        (8, "prev_term"),
        (10, "commit"),
        (12, "index"),
        (14, "entry_term"),
    ):
        row[name] = int.from_bytes(payload[offset : offset + 2], "little")
    row.update(
        event=payload[16],
        success=payload[17],
        flags=payload[18],
        serial=int.from_bytes(payload[19:23], "little"),
    )
    if row["term"] > 65534 or row["event"] > 23 or row["success"] > 1:
        raise ValueError("Invalid RPC field")
    if row["kind"] == "APPEND":
        row["empty_append"] = row["index"] == 0
    return row


def seconds(us):
    return f"{us // 1000000}.{us % 1000000:06d}"


def periods(times):
    gaps = [(b - a) / 1000 for a, b in zip(times, times[1:])]
    return {
        "frames": len(times),
        "intervals": len(gaps),
        "mean_interval_ms": statistics.mean(gaps) if gaps else None,
        "min_interval_ms": min(gaps) if gaps else None,
        "max_interval_ms": max(gaps) if gaps else None,
    }


def analyze_capture(path, decoded_csv=None):
    path = Path(path)
    if decoded_csv is not None and path.resolve() == Path(decoded_csv).resolve():
        raise ValueError("Decoded output must not overwrite the input capture")
    quality = Counter()
    ids = Counter()
    kinds = Counter()
    rpc_kinds = Counter()
    slots = {}
    previous_time = {}
    refs = defaultdict(list)
    ref_details = defaultdict(list)
    appends = defaultdict(list)
    ref_last = {}
    ref_quality = defaultdict(Counter)
    timeline = []
    first = last = None

    with path.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            match = LINE.fullmatch(line)
            if not match:
                quality["unparsed_lines"] += 1
                continue
            timestamp, bus, raw_id, raw_data = match.groups()
            at = int(Decimal(timestamp) * 1000000)
            if bus in previous_time and at < previous_time[bus]:
                raise ValueError(
                    f"Timestamp moved backwards on {bus}, line {line_number}; use one chronological capture"
                )
            previous_time[bus] = at
            ident = int(raw_id, 16)
            if (
                len(raw_id) > 3
                or ident > 0x7FF
                or len(raw_data) % 2
                or len(raw_data) > 16
            ):
                quality["unsupported_frames"] += 1
                continue
            data = bytes.fromhex(raw_data)
            quality["parsed_frames"] += 1
            first = at if first is None else min(first, at)
            last = at if last is None else max(last, at)
            ids[f"{bus}:{ident:03X}"] += 1
            known = (
                ident in CATALOG
                or 0x81 <= ident <= 0x83
                or 0x111 <= ident <= 0x113
                or 0x410 <= ident <= 0x43F
            )
            if not known:
                quality["unknown_ids"] += 1
                continue
            if len(data) != 8:
                quality["invalid_dlc"] += 1
                continue
            if crc(data[:7]) != data[7]:
                quality["bad_frame_crc"] += 1
                continue
            base = {
                "timestamp_s": seconds(at),
                "interface": bus,
                "can_id": f"{ident:03X}",
                "payload_hex": data.hex(),
            }
            if ident in CATALOG:
                name = CATALOG[ident]
                kinds[f"{bus}:{name}"] += 1
                timeline.append(dict(base, kind=name, sequence=data[0] & 15))
            elif 0x111 <= ident <= 0x113:
                kinds[f"{bus}:HELLO"] += 1
                timeline.append(
                    dict(base, kind="HELLO", source=ident - 0x110, sequence=data[0])
                )
            elif 0x81 <= ident <= 0x83:
                term = int.from_bytes(data[1:3], "little")
                if not 1 <= term <= 65534:
                    quality["invalid_ref"] += 1
                    continue
                src, cycle = ident - 0x80, data[0]
                key = f"{bus}:N{src}"
                kinds[f"{bus}:REF"] += 1
                row = dict(
                    base,
                    kind="REF",
                    source=src,
                    sequence=cycle,
                    term=term,
                    master_time_low_us=int.from_bytes(data[3:7], "little"),
                )
                timeline.append(row)
                ref_details[key].append(row)
                old = ref_last.get(key)
                if old is not None and old[1] == term and at - old[0] <= 250000:
                    delta = (cycle - old[2]) & 255
                    if delta == 0:
                        ref_quality[key]["duplicate_cycles"] += 1
                        continue
                    if delta >= 128:
                        ref_quality[key]["out_of_order_cycles"] += 1
                        continue
                    ref_quality[key]["missing_cycles_within_250ms"] += delta - 1
                # Keep cadence separately across term changes/restarts; long outages
                # remain visible as gaps rather than being silently discarded.
                ref_last[key] = (at, term, cycle)
                refs[(key, term)].append(at)
            else:
                quality["rpc_fragments"] += 1
                src, dst, fragment = (ident >> 4) & 3, (ident >> 2) & 3, ident & 3
                key = (bus, src, dst)
                seq = data[0]
                old = slots.get(key)
                new = (
                    old is None
                    or at - old["at"] > 250000
                    or (seq != old["seq"] and ((seq - old["seq"]) & 255) < 128)
                )
                if new:
                    if old and not old["done"]:
                        quality["incomplete_rpc_sequences"] += 1
                    old = {"at": at, "seq": seq, "pieces": {}, "done": False}
                    slots[key] = old
                if seq != old["seq"] or old["done"]:
                    quality["duplicate_or_stale_fragments"] += 1
                    continue
                piece = data[1:7]
                if fragment in old["pieces"]:
                    if old["pieces"][fragment] != piece:
                        quality["conflicting_fragments"] += 1
                        old["done"] = True
                    else:
                        quality["duplicate_or_stale_fragments"] += 1
                    continue
                old["pieces"][fragment] = piece
                if len(old["pieces"]) != 4:
                    continue
                old["done"] = True
                payload = b"".join(old["pieces"][i] for i in range(4))
                try:
                    row = decode_rpc(payload, src, dst)
                except ValueError:
                    quality["invalid_rpc"] += 1
                    continue
                row.update(
                    base,
                    can_id=f"{ident & ~3:03X}-{(ident & ~3) + 3:03X}",
                    payload_hex=payload.hex(),
                    first_fragment_s=seconds(old["at"]),
                    sequence=seq,
                )
                timeline.append(row)
                quality["decoded_rpcs"] += 1
                rpc_kinds[f"{bus}:{row['kind']}"] += 1
                if row["kind"] == "APPEND" and row["empty_append"]:
                    appends[f"{bus}:N{src}->N{dst}:term{row['term']}"].append(old["at"])

    quality["incomplete_rpc_sequences"] += sum(not s["done"] for s in slots.values())
    if not quality["parsed_frames"]:
        raise ValueError(
            "No supported candump -L frames found; an empty/unreadable capture cannot pass"
        )
    streams = {}
    for key, rows in ref_details.items():
        terms = sorted({r["term"] for r in rows})
        streams[key] = dict(
            (
                periods([t for term in terms for t in refs[(key, term)]])
                if len(terms) == 1
                else {
                    "frames": sum(len(refs[(key, term)]) for term in terms),
                    "mean_interval_ms": None,
                    "max_interval_ms": None,
                }
            ),
            terms=terms,
            by_term={str(term): periods(refs[(key, term)]) for term in terms},
            **ref_quality[key],
            first=rows[0],
            last=rows[-1],
        )
    if decoded_csv is not None:
        with Path(decoded_csv).open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(timeline)
    return {
        "parsed_frames": quality["parsed_frames"],
        "duration_s": (last - first) / 1000000,
        "ids": dict(sorted(ids.items())),
        "valid_frame_types": dict(sorted(kinds.items())),
        "ref_streams": streams,
        "rpc_types": dict(sorted(rpc_kinds.items())),
        "empty_append_streams": {k: periods(v) for k, v in sorted(appends.items())},
        "vote_requests_observed": sum(
            v for k, v in rpc_kinds.items() if k.endswith(":REQ_VOTE")
        ),
        "prevote_requests_observed": sum(
            v for k, v in rpc_kinds.items() if k.endswith(":PREVOTE")
        ),
        "quality": dict(sorted(quality.items())),
        "note": "Counts are per-interface observations, not unique events or proof of node acceptance. "
        "No vote observed is not proof of no vote if frames/fragments are missing. "
        "Cadence uses receive timestamps (APPEND first fragment); it is not GPIO timing. "
        "Incomplete RPCs can result from capture boundaries, capture loss, or actual bus loss.",
    }
