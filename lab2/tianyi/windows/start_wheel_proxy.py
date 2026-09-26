"""Local convenience launcher for the unchanged course Windows proxy.

Prompts for the Pi IPv4 address and selects the laptop address from its route.
Only overrides the course proxy's network constants in memory. The course
proxy performs its normal wheel initialization when the user clicks connect.
"""

import ipaddress
import os
from pathlib import Path
import socket
import sys


def laptop_address_for(pi_address):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        # UDP connect chooses the local route; it does not send a UDP packet.
        route.connect((pi_address, 8000))
        return route.getsockname()[0]


def main():
    print("Course Windows wheel proxy launcher")
    print("Find the Pi address in its SSH shell with:")
    print("  nmcli -g IP4.ADDRESS device show wlan0")
    print("Enter only the address, without /17 or another slash suffix.")
    while True:
        try:
            pi_address = str(ipaddress.IPv4Address(input("Pi IPv4 address: ").strip()))
            break
        except ipaddress.AddressValueError:
            print("Enter four numbers separated by dots, as printed by the Pi.")

    local_address = laptop_address_for(pi_address)
    configured = os.environ.get("LOGITECH_WHEEL_REPO", "").strip().strip('"')
    candidates = ([Path(configured)] if configured else []) + [
        parent / "logitech-wheel-dev-updated-f26"
        for parent in Path(__file__).resolve().parents
    ]
    repository = next(
        (candidate for candidate in candidates if (candidate / "proxy_gui.py").is_file()),
        candidates[0],
    )
    if not (repository / "proxy_gui.py").is_file():
        raise RuntimeError("Course proxy not found at " + str(repository))
    sys.path.insert(0, str(repository))
    import proxy_gui

    proxy_gui.REMOTE_HOST = pi_address
    proxy_gui.LOCAL_HOST = local_address
    proxy_gui.S_PORT = 8000
    proxy_gui.R_PORT = 8001
    print("Laptop %s -> Pi %s, UDP port 8000" % (local_address, pi_address))
    print("This selects an address; it does not prove the Pi is reachable.")
    print("Clamp the wheel and keep hands clear; connect gives a short bump.")
    print("Click connect in the course window. Keep the wheel clamped and hands clear.")
    print("With the Part 2 Pi bridge, No data is expected on the return-force channel.")
    print("With a return sender, look for Received lines; force bytes are applied automatically.")
    print("Toggle feedback controls a separate effect; leave it alone for this check.", flush=True)
    app = proxy_gui.QtWidgets.QApplication(sys.argv)
    window = proxy_gui.MyMainwindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ImportError) as error:
        print("Could not start the proxy: %s" % error, file=sys.stderr)
        sys.exit(1)
