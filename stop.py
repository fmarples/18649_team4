"""Stop this launcher's wheel GUI and Pi bridge, leaving the Pi and G HUB on."""
from tools.wheel_session import main

if __name__ == '__main__':
    raise SystemExit(main('stop'))
