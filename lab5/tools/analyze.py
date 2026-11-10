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
from can_capture import analyze_capture


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


def traffic(path, decoded_csv=None):
    return analyze_capture(path, decoded_csv)


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
                    index, term, event = (data[k] for k in ("index", "term", "event"))
                    if (
                        any(type(v) is not int for v in (index, term, event))
                        or not 1 <= index <= 30000
                        or not 1 <= term <= 65534
                        or not 0 <= event < len(NAMES)
                    ):
                        raise ValueError("Invalid committed-entry field")
                    row = index, (term, NAMES[event])
                elif "COMMIT" in line:
                    raise ValueError("Missing committed-entry field")
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise ValueError(
                    f"Invalid JSON/committed row in {path}: {line}"
                ) from exc
        else:
            m = re.search(r"(?:COMMIT|LOG) index=(\d+) term=(\d+) event=(\w+)", line)
            if m:
                row = int(m[1]), (int(m[2]), m[3])
                if (
                    not 1 <= row[0] <= 30000
                    or not 1 <= row[1][0] <= 65534
                    or m[3] not in NAMES
                ):
                    raise ValueError(f"Invalid committed row in {path}: {line}")
            elif re.search(r"\b(?:COMMIT|LOG)\b.*index=", line):
                raise ValueError(f"Malformed committed row in {path}: {line}")
        if row:
            index, value = row
            if index in entries and entries[index] != value:
                raise ValueError(f"Conflicting index {index} in {path}")
            entries[index] = value
    return entries


def logs(paths):
    if len(paths) < 2:
        raise ValueError(
            "Compare at least two node logs (all three for the full-cluster check)"
        )
    data = [read_log(p) for p in paths]
    if not data or any(not d for d in data):
        raise ValueError("Every capture must contain committed entries")
    end = min(max(d) for d in data)
    missing = [[i for i in range(1, end + 1) if i not in d] for d in data]
    conflicts = [
        i for i in range(1, end + 1) if len({d[i] for d in data if i in d}) > 1
    ]
    return dict(
        through_index=end,
        last_indices=[max(d) for d in data],
        missing_indices=missing,
        conflicts=conflicts,
        common_prefix_agrees=not conflicts and not any(missing),
        identical_complete_logs=all(d == data[0] for d in data) and not any(missing),
        note="A missing capture row is not a proven Raft conflict. Compare full committed histories after traffic settles. Repeated identical rows are deduplicated, so this comparison alone does not prove exactly-once display.",
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=("edges", "candump", "logs"))
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument(
        "--decoded-csv",
        type=Path,
        help="candump only: save decoded frames/RPCs for inspection",
    )
    a = ap.parse_args()
    if a.kind != "logs" and len(a.files) != 1:
        ap.error("Use exactly one capture")
    if a.decoded_csv and a.kind != "candump":
        ap.error("--decoded-csv is only for candump")
    result = (
        logs(a.files)
        if a.kind == "logs"
        else (
            edges(a.files[0])
            if a.kind == "edges"
            else traffic(a.files[0], a.decoded_csv)
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
