"""Analyze real captures without turning assumptions into measurements.

edges: CSV columns signal,time_s containing rising edges on one scope timebase.
candump: `candump -L any` text (timestamp, interface, ID#hex).
logs: Nucleo COMMIT/LOG text or Pi events.csv; compare committed prefixes.
"""

import argparse
import csv
import json
from pathlib import Path
import re
import statistics


def edges(path):
    groups = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            groups.setdefault(row["signal"], []).append(float(row["time_s"]))
    result = {}
    for name, times in groups.items():
        times.sort()
        periods = [b - a for a, b in zip(times, times[1:])]
        result[name] = dict(
            edges=len(times),
            periods=len(periods),
            mean_period_s=statistics.mean(periods) if periods else None,
            peak_to_peak_period_jitter_us=(
                (max(periods) - min(periods)) * 1e6 if periods else None
            ),
        )
    if "FL" in groups and "RL" in groups and groups["FL"] and groups["RL"]:
        # One-to-one pairing after common trigger. Do not hide dropped edges by
        # matching every edge to whichever neighbour happens to be nearest.
        a, b = groups["FL"], groups["RL"]
        skew = [(y - x) * 1e6 for x, y in zip(a, b)]
        result["FL_RL"] = dict(
            equal_edge_counts=len(a) == len(b),
            paired_edges=len(skew),
            max_absolute_skew_us=max(map(abs, skew)),
            ten_edge_1ms_check=len(skew) >= 10
            and len(a) == len(b)
            and max(map(abs, skew)) <= 1000,
        )
    return result


def traffic(path):
    groups = {}
    frames = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.search(r"\(([\d.]+)\)\s+(\S+)\s+([0-9A-Fa-f]+)#([0-9A-Fa-f]+)", line)
        if not m:
            continue
        at, bus, ident, data = m.groups()
        frames += 1
        ident = int(ident, 16)
        if 0x81 <= ident <= 0x83 and len(data) == 16:
            groups.setdefault(f"{bus}:N{ident-0x80}", []).append(float(at))
    refs = {}
    for key, ts in groups.items():
        intervals = [(b - a) * 1000 for a, b in zip(ts, ts[1:])]
        refs[key] = dict(
            frames=len(ts),
            mean_interval_ms=statistics.mean(intervals) if intervals else None,
            max_interval_ms=max(intervals) if intervals else None,
        )
    return dict(
        parsed_frames=frames,
        ref_streams=refs,
        note="Bus capture timestamps measure reception intervals, not GPIO skew or handover phase.",
    )


NAMES = (
    [
        "NOOP",
        "COCKPIT_OK",
        "COCKPIT_ERROR",
        "NODE_1_UP",
        "NODE_1_DOWN",
        "NODE_2_UP",
        "NODE_2_DOWN",
        "NODE_3_UP",
        "NODE_3_DOWN",
    ]
    + [
        f"CANLINK_{n}_{b}_{s}"
        for n in (1, 2, 3)
        for b in ("A", "B")
        for s in ("UP", "DOWN")
    ]
    + ["EVENT_N1", "EVENT_N2", "EVENT_N3"]
)


def read_log(path):
    entries = {}
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if lines and lines[0].startswith("mono_s,"):
        lines = [r["detail"] for r in csv.DictReader(lines) if r["event"] == "COMMIT"]
    for line in lines:
        row = None
        if "{" in line:
            try:
                data = json.loads(line[line.index("{") :])
                if all(k in data for k in ("index", "term", "event")):
                    row = int(data["index"]), (int(data["term"]), NAMES[data["event"]])
            except (ValueError, KeyError, IndexError, TypeError):
                pass
        else:
            m = re.search(r"(?:COMMIT|LOG) index=(\d+) term=(\d+) event=(\w+)", line)
            if m:
                row = int(m[1]), (int(m[2]), m[3])
        if row:
            index, value = row
            if index in entries and entries[index] != value:
                raise ValueError(f"Conflicting index {index} in {path}")
            entries[index] = value
    return entries


def logs(paths):
    data = [read_log(p) for p in paths]
    if not data or any(not d for d in data):
        raise ValueError("Every capture must contain committed entries")
    end = min(max(d) for d in data)
    missing = [[i for i in range(1, end + 1) if i not in d] for d in data]
    conflicts = [i for i in range(1, end + 1) if len({d.get(i) for d in data}) > 1]
    return dict(
        through_index=end,
        last_indices=[max(d) for d in data],
        missing_indices=missing,
        conflicts=conflicts,
        common_prefix_agrees=not conflicts and not any(missing),
        identical_complete_logs=all(d == data[0] for d in data) and not any(missing),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=("edges", "candump", "logs"))
    ap.add_argument("files", nargs="+", type=Path)
    a = ap.parse_args()
    if a.kind != "logs" and len(a.files) != 1:
        ap.error("Use exactly one capture")
    result = (
        logs(a.files)
        if a.kind == "logs"
        else edges(a.files[0]) if a.kind == "edges" else traffic(a.files[0])
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
