#!/usr/bin/env python3
"""Extract legacy snapshots or --tasks named elapsed-time records from serial logs."""
import argparse, csv, re
from pathlib import Path

PATTERN = re.compile(r"OBS_MAX_US\s+uptime_ms=(\d+)\s+rx_dispatch=(\d+)\s+can_tx=(\d+)\s+steer_drive=(\d+)\s+hb_mon=(\d+)\s+hb_tx=(\d+)\s+pid=(\d+)\s+test_btn=(\d+)\s+relay=(\d+)\s+counts=(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)")
FIELDS = ["uptime_ms","rx_dispatch_max_us","can_tx_max_us","steer_drive_max_us","hb_mon_max_us","hb_tx_max_us","pid_max_us","test_btn_max_us","relay_max_us","rx_dispatch_count","can_tx_count","steer_drive_count","hb_mon_count","hb_tx_count","pid_count","test_btn_count","relay_count"]

TASK_PATTERN = re.compile(r"OBS_TASK\s+zone=(N[23])\s+uptime_ms=(\d+)\s+name=([a-z_]+)\s+max_cycles=(\d+)\s+max_us=(\d+)\s+count=(\d+)\s*$")
TASK_FIELDS = ["zone", "uptime_ms", "task", "max_cycles", "max_us", "count"]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("console_log")
    ap.add_argument("--out", default="stm32_timing.csv")
    ap.add_argument("--tasks", action="store_true", help="parse named OBS_TASK records; count=0 means unmeasured")
    args=ap.parse_args()
    fields = TASK_FIELDS if args.tasks else FIELDS
    pattern = TASK_PATTERN if args.tasks else PATTERN
    label = "OBS_TASK" if args.tasks else "OBS_MAX_US"
    matched=0
    with open(args.console_log, encoding="utf-8", errors="replace") as src, open(args.out,"w",newline="", encoding="utf-8") as dst:
        writer=csv.DictWriter(dst,fieldnames=fields); writer.writeheader()
        for line_number, line in enumerate(src, start=1):
            m=pattern.search(line)
            if not m:
                if args.tasks and "OBS_TASK" in line:
                    raise SystemExit(f"Malformed OBS_TASK at line {line_number}; retain the raw log and recapture.")
                continue
            writer.writerow(dict(zip(fields,m.groups()))); matched+=1
    print(f"Extracted {matched} {label} records to {Path(args.out).resolve()}")
    if not matched: raise SystemExit(f"No {label} lines found; verify firmware and capture.")
if __name__=="__main__": main()
