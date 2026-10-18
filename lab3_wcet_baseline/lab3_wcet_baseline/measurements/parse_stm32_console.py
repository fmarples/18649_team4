#!/usr/bin/env python3
"""Extract OBS_MAX_US snapshots from a captured Zephyr serial-console text file."""
import argparse, csv, re
from pathlib import Path

PATTERN = re.compile(r"OBS_MAX_US\s+uptime_ms=(\d+)\s+rx_dispatch=(\d+)\s+can_tx=(\d+)\s+steer_drive=(\d+)\s+hb_mon=(\d+)\s+hb_tx=(\d+)\s+pid=(\d+)\s+test_btn=(\d+)\s+relay=(\d+)\s+counts=(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)")
FIELDS = ["uptime_ms","rx_dispatch_max_us","can_tx_max_us","steer_drive_max_us","hb_mon_max_us","hb_tx_max_us","pid_max_us","test_btn_max_us","relay_max_us","rx_dispatch_count","can_tx_count","steer_drive_count","hb_mon_count","hb_tx_count","pid_count","test_btn_count","relay_count"]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("console_log")
    ap.add_argument("--out", default="stm32_timing.csv")
    args=ap.parse_args()
    matched=0
    with open(args.console_log, errors="replace") as src, open(args.out,"w",newline="") as dst:
        writer=csv.DictWriter(dst,fieldnames=FIELDS); writer.writeheader()
        for line in src:
            m=PATTERN.search(line)
            if not m: continue
            writer.writerow(dict(zip(FIELDS,map(int,m.groups())))); matched+=1
    print(f"Extracted {matched} OBS_MAX_US snapshots to {Path(args.out).resolve()}")
    if not matched: raise SystemExit("No OBS_MAX_US lines found; verify that the firmware is running and the console log was captured.")
if __name__=="__main__": main()
