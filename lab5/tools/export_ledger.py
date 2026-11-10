"""Export a consistent read-only snapshot of the Pi's durable display history.

Run on the Pi while idle, or on a SQLite-consistent backup. A live WAL database
must not be copied by taking display.sqlite alone. This does not clear Raft or
display state, and does not wait for the application's in-memory queue to drain.
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def snapshot(path):
    path = Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        records = db.execute(
            "SELECT idx,term,event,row FROM events ORDER BY idx"
        ).fetchall()
    result = []
    for idx, term, event, raw in records:
        row = json.loads(raw)
        if (
            not isinstance(row, dict)
            or any(type(v) is not int for v in (idx, term, event))
            or not 1 <= idx <= 30000
            or not 1 <= term <= 65534
            or not 0 <= event <= 23
            or any(type(row.get(k)) is not int for k in ("index", "term", "event"))
            or (row["index"], row["term"], row["event"]) != (idx, term, event)
        ):
            raise ValueError(
                f"Inconsistent ledger row {idx}; preserve the database for diagnosis"
            )
        result.append(row)
    if not result:
        raise ValueError(
            "The ledger has no committed entries; an empty history cannot pass"
        )
    return result


def export(path, output):
    path, output = Path(path), Path(output)
    if path.resolve() == output.resolve():
        raise ValueError("Output must not overwrite the database")
    rows = snapshot(path)
    # Exclusive creation preserves earlier evidence if a filename is reused.
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument(
        "output", type=Path, help="new JSONL file; existing files are not overwritten"
    )
    args = parser.parse_args()
    count = export(args.database, args.output)
    print(
        f"Exported {count} durable entries to {args.output}; check queue/error counters before comparing."
    )


if __name__ == "__main__":
    main()
