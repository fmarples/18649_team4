"""Close the wheel GUI opened by lab5/start.py; the Pi cockpit service keeps running."""
from session import main

if __name__ == '__main__':
    raise SystemExit(main('stop'))
