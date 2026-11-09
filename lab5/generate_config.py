"""Validate the shared config and generate the C constants used on all nodes."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path=ROOT / "config.json"):
    c = json.loads(Path(path).read_text())
    if c["N"] != 3:
        raise ValueError("Three voters are implemented; quorum is two")
    c["debug"] = c["Debug"]
    if c["nodes"] != {"cockpit": 1, "front": 2, "rear": 3}:
        raise ValueError(
            "This implementation has three fixed voters: cockpit/front/rear = 1/2/3"
        )
    if c["default_leader"] not in ("cockpit", "none", "random"):
        raise ValueError("default_leader must be cockpit, none or random")
    for k, v in (
        ("heartbeat_ms", 20),
        ("append_ms", 100),
        ("missed_heartbeats", 3),
        ("election_timeout_jitter_ms", 39),
        ("log_size", 30000),
    ):
        if c[k] != v:
            raise ValueError(f"{k} must be {v} for this handout")
    if type(c["seed"]) is not int or not 1 <= c["seed"] <= 0xFFFFFFFF:
        raise ValueError("seed must be a nonzero uint32")
    if type(c["debug"]) is not bool:
        raise ValueError("debug must be boolean")
    if not 0 <= c["can_delay_us"] <= 10000:
        raise ValueError("invalid CAN delay estimate")
    return c


def generate(source, output):
    c = load(source)
    values = {
        "HEARTBEAT_MS": c["heartbeat_ms"],
        "APPEND_MS": c["append_ms"],
        "MISSED_HEARTBEATS": c["missed_heartbeats"],
        "JITTER_MS": c["election_timeout_jitter_ms"],
        "CAPACITY": c["log_size"],
        "DEFAULT_LEADER": 1 if c["default_leader"] == "cockpit" else 0,
        "SEED": c["seed"],
        "DEBUG": int(c["debug"]),
        "CAN_DELAY_US": c["can_delay_us"],
    }
    Path(output).write_text(
        "/* Generated from lab5/config.json; do not edit. */\n"
        + "\n".join(f"#define L5_CFG_{k} {v}U" for k, v in values.items())
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=ROOT / "config.json")
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    generate(a.source, a.output)
