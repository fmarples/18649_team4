"""Read bridge CSV offline. MCU timestamps are diagnostics, not scope timing proof."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import statistics

def summarize(rows):
    states = Counter(); intervals = []; missing = 0; discontinuities = 0
    valid_counts = [0, 0, 0]; previous = None; count = 0
    for row in rows:
        seq, tick = int(row['status_seq']), int(row['stm_ms'])
        states[int(row['state'])] += 1; count += 1
        if previous is not None:
            gap = (seq - previous[0]) & 0xffffffff
            dt = (tick - previous[1]) & 0xffffffff
            if gap == 1 and dt < 0x80000000: intervals.append(dt)
            elif 1 < gap < 0x80000000: missing += gap - 1
            else: discontinuities += 1
        previous = seq, tick
        mask = int(row['current_valid_mask'])
        for i, name in enumerate(('left', 'right', 'servo')):
            if mask & (1 << i) and int(row['current_' + name + '_mA']) != -2147483648:
                valid_counts[i] += 1
    if not count: raise ValueError('No status frames in this CSV.')
    return dict(frames=count, states=dict(states), missing_sequence_numbers=missing,
                sequence_discontinuities=discontinuities,
                consecutive_mcu_intervals=len(intervals),
                mcu_interval_min_ms=min(intervals) if intervals else None,
                mcu_interval_max_ms=max(intervals) if intervals else None,
                mcu_interval_mean_ms=statistics.mean(intervals) if intervals else None,
                mcu_intervals_outside_18_22_ms=sum(not 18 <= x <= 22 for x in intervals),
                valid_current_frames=dict(zip(('left', 'right', 'servo'), valid_counts)),
                limitation='MCU construction timestamps only; excludes UART scheduling/wire and actuator timing. Scope captures are still required.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    args = parser.parse_args()
    with args.csv.open(newline='', encoding='utf-8-sig') as stream:
        result = summarize(csv.DictReader(stream))
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
