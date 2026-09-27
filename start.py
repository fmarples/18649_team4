"""Start the Pi bridge and wheel GUI in the background; keep hands clear."""
from tools.wheel_session import main

if __name__ == '__main__':
    raise SystemExit(main('start'))
