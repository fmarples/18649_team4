"""Compatibility entry point for the bounded startup/direction check.

The old 100% / five-second test is retired. --duty is now required.
LEFT, RIGHT and BOTH use the 200 ms startup check. See check_motor_startup.py for the safety interlocks.
"""
from check_motor_startup import main


if __name__ == '__main__':
    main()
