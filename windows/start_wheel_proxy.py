"""Launch the course wheel GUI with read-only Raw log and Current chart windows.

The course proxy stays external and unchanged. Pi status telemetry arrives on
its own port, never on the course proxy's force-feedback input.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pi.part2_protocol import STATUS_UDP_PORT


def laptop_address_for(pi_address):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        # UDP connect chooses the local route; it does not send a UDP packet.
        route.connect((pi_address, 8000))
        return route.getsockname()[0]


# Resolve the installed course proxy without copying or modifying upstream files.
def course_repository():
    configured = os.environ.get('LOGITECH_WHEEL_REPO', '').strip().strip('"')
    candidates = ([Path(configured)] if configured else []) + [
        parent / 'logitech-wheel-dev-updated-f26'
        for parent in Path(__file__).resolve().parents
    ]
    repository = next(
        (candidate for candidate in candidates if (candidate / 'proxy_gui.py').is_file()),
        candidates[0],
    )
    if not (repository / 'proxy_gui.py').is_file():
        raise RuntimeError('Course proxy not found at ' + str(repository))
    return repository


# Monitor-only uses the same receiver/views without importing or initializing the wheel SDK.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pi', type=ipaddress.IPv4Address, help='Pi IPv4; prompts when omitted')
    parser.add_argument('--telemetry-port', type=int, default=STATUS_UDP_PORT)
    parser.add_argument('--monitor-only', action='store_true', help='No wheel SDK or command transmission')
    parser.add_argument('--current-channels', nargs='+', choices=('left', 'right', 'servo'),
                        default=['left', 'right', 'servo'],
                        help='Connected sensors: left/A0, right/A1, servo/A3; omit any unwired channel')
    parser.add_argument('--connect', action='store_true', help='Connect wheel automatically; keep hands clear')
    parser.add_argument('--ready-file', type=Path, help='Launcher readiness report after wheel SDK connects')
    parser.add_argument('--log-dir', type=Path, default=REPO / 'logs/wheel-gui')
    args = parser.parse_args()
    if not 1 <= args.telemetry_port <= 65535 or args.telemetry_port in (8000, 8001):
        parser.error('Telemetry needs a separate port, not 8000 or 8001')
    if args.connect and args.monitor_only:
        parser.error('--connect cannot be used with --monitor-only')
    from PyQt5 import QtWidgets, QtCore
    from windows.telemetry_gui import SessionLog, TelemetryWindows
    app = QtWidgets.QApplication([sys.argv[0]])
    log = SessionLog(args.log_dir)
    monitor = None
    try:
        print('Course Windows wheel proxy launcher')
        print('Find the Pi address with: nmcli -g IP4.ADDRESS device show wlan0')
        pi_address = str(args.pi) if args.pi else None
        while pi_address is None:
            try:
                pi_address = str(ipaddress.IPv4Address(input('Pi IPv4 address: ').strip()))
            except ipaddress.AddressValueError:
                print('Enter only the IPv4 address, without a slash suffix.')
        local_address = laptop_address_for(pi_address)
        if args.monitor_only:
            window = QtWidgets.QMainWindow()
            window.setWindowTitle('Wheel telemetry monitor')
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.addWidget(QtWidgets.QLabel('Read-only monitor. No wheel or actuator commands.'))
            window.setCentralWidget(widget)
            print(f'Start Pi bridge with --telemetry-host {local_address} for monitor-only use.')
        else:
            sys.path.insert(0, str(course_repository()))
            import proxy_gui
            proxy_gui.REMOTE_HOST = pi_address
            proxy_gui.LOCAL_HOST = local_address
            proxy_gui.S_PORT = 8000
            proxy_gui.R_PORT = 8001
            window = proxy_gui.MyMainwindow()
            # The course default is 50 ms, leaving only 30 ms before the Pi's
            # 80 ms freshness limit. Match the intended 20 ms command cadence.
            for timer in (window.update_timer, window.transmit_timer):
                timer.setInterval(20)
                timer.setTimerType(QtCore.Qt.PreciseTimer)
            from windows.wheel_input_log import InputLoggingSocket
            inputs = InputLoggingSocket(window.send_socket, log)
            window.send_socket = inputs
            window.connect_button.clicked.connect(inputs.reset)
            window.stop_button.clicked.connect(inputs.reset)
            window.setWindowTitle('Wheel proxy')
            print(f'Laptop {local_address} -> Pi {pi_address}, command UDP 8000')
            print('Clamp the wheel and keep hands clear; connect gives a short bump.')
            print('Leave Toggle feedback alone. The existing force input is separate from telemetry.')
        monitor = TelemetryWindows(window, pi_address, local_address, args.telemetry_port, log,
                                   connected_channels=args.current_channels)
        print('Raw log and Current chart are read-only. Logs: ' + str(log.path))
        window.show()
        if args.connect:
            # Run after the window exists. Report success only after SDK wheel detection.
            def connect_for_launcher():
                try:
                    window.connect_to_wheel()
                    if not window.transmit_timer.isActive() or not proxy_gui.lsw.is_connected(0):
                        raise RuntimeError('Logitech wheel not connected. Check power, USB and G HUB.')
                    if args.ready_file:
                        temporary = args.ready_file.with_suffix('.tmp')
                        temporary.write_text(json.dumps({'pid': os.getpid(), 'connected': True}), encoding='utf-8')
                        temporary.replace(args.ready_file)
                except Exception:
                    log.exception(*sys.exc_info())
                    window.stop()
                    app.exit(1)
            QtCore.QTimer.singleShot(0, connect_for_launcher)
        return app.exec_()
    except Exception:
        log.exception(*sys.exc_info())
        return 1
    finally:
        if monitor is not None:
            monitor.close()
        log.close()


if __name__ == '__main__':
    sys.exit(main())
