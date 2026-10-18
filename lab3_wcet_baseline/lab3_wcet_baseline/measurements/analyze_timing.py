#!/usr/bin/env python3
"""Summarize the CSV emitted by pi/cockpit_bridge.py (no fabricated timing values)."""
import argparse, csv, math, statistics
from collections import Counter, defaultdict

def percentile(values, q):
    if not values: return None
    xs=sorted(values)
    idx=max(0, min(len(xs)-1, math.ceil(q*len(xs))-1))
    return xs[idx]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('csv_path')
    args=ap.parse_args()
    with open(args.csv_path, newline='') as f: rows=list(csv.DictReader(f))
    print(f"Rows: {len(rows)}")
    counts=Counter(r.get('event','') for r in rows)
    print('\nEvent counts:')
    for key,count in sorted(counts.items()): print(f"  {key or '(empty)'}: {count}")
    for event in ('UDP_TO_CMD_TX', 'CTRL_SEND_GROUP'):
        vals=[]
        for r in rows:
            if r.get('event')==event and r.get('latency_us'):
                try: vals.append(float(r['latency_us']))
                except ValueError: pass
        label = "UDP receive to pre-send marker" if event == "UDP_TO_CMD_TX" else "dual SocketCAN send-call duration (not wire latency)"
        print(f"\n{event} ({label}), n={len(vals)}")
        if vals:
            print(f"  min={min(vals):.3f} us  mean={statistics.mean(vals):.3f} us  max={max(vals):.3f} us  p99={percentile(vals,.99):.3f} us")
    times=defaultdict(list)
    for r in rows:
        try: t=int(r['mono_ns'])
        except (ValueError, KeyError): continue
        if r.get('event') in ('UDP_RX','CAN_RX','CAN_TX'): times[(r['event'],r.get('interface',''))].append(t)
    print('\nObserved event inter-arrivals (monotonic userspace timestamps):')
    for (event,iface), stamps in sorted(times.items()):
        stamps.sort(); diffs=[(b-a)/1e6 for a,b in zip(stamps,stamps[1:])]
        if diffs: print(f"  {event} {iface}: n={len(diffs)} min={min(diffs):.3f} ms mean={statistics.mean(diffs):.3f} ms max={max(diffs):.3f} ms p99={percentile(diffs,.99):.3f} ms")
    print('\nReminder: this report is descriptive measurement, not a mathematical WCET proof.')
if __name__=='__main__': main()
