"""Check the generated Zephyr PWM configuration, not the physical waveform."""
import argparse
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dts", default="build/motor-test/zephyr/zephyr.dts")
    parser.add_argument("--period-ns", required=True, type=int)
    args = parser.parse_args()
    tree = Path(args.dts).read_text(encoding="utf-8")
    for label, controller, channel in (("left_pwm", "pwm3", 1), ("right_pwm", "pwm2", 3)):
        match = re.search(
            rf"\b{label}:\s+\w+\s*\{{\s*pwms\s*=\s*<\s*&([\w]+)"
            r"\s+(0x[\da-f]+|\d+)\s+(0x[\da-f]+|\d+)\s+(0x[\da-f]+|\d+)\s*>",
            tree,
        )
        if not match:
            raise SystemExit(f"FAIL: no PWM spec for {label} in generated DTS")
        actual = (match[1], int(match[2], 0), int(match[3], 0), int(match[4], 0))
        expected = (controller, channel, args.period_ns, 0)
        if actual != expected:
            raise SystemExit(f"FAIL: {label}: {actual}; expected {expected}")
        print(f"PASS: {label}: {actual}; configured period, not scope verification")


if __name__ == "__main__":
    main()
