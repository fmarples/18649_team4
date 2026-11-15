"""Lab 5 bench session: keep the Pi cockpit service up and own one wheel GUI.

Used by lab5/start.py and lab5/stop.py. The Pi cockpit is a boot service and
both Nucleos run from flash, so start only restarts that service when it is
down, opens the course wheel GUI connected, and reports whether the cluster is
ready. Stop closes only the GUI this session opened; the Pi service keeps
running. Nothing here deploys Pi files or flashes firmware.
"""
import argparse
import ipaddress
import json
import logging
import os
from pathlib import Path
import shlex
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from lab3_demo.pi_ssh import sudo, sudo_password  # noqa: E402
from tools.wheel_session import (  # noqa: E402
    ensure_ghub, launch_proxy, proxy_alive, session_lock, ssh, stop_proxy)

LOG = logging.getLogger(__name__)
HOST = 'wheelpi'
UNIT = 'team4-lab5-cockpit.service'
STATE = 'logs/lab5/session/state.json'


def load_state(root):
    path = root / STATE
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


# Stop only the wheel GUI recorded by start; the Pi cockpit service is not this session's to stop.
def stop(root):
    state = load_state(root)
    if state is None:
        return
    stop_proxy(state['proxy'])
    (root / STATE).unlink()
    LOG.info('Stopped wheel GUI %s', state['proxy'])


# The cockpit is a boot service: start it only when it is down, and require it to come up.
def ensure_service():
    query = f'systemctl is-active {UNIT}; true'
    if ssh(HOST, query) == 'active':
        return
    sudo(sudo_password(), f'systemctl start {UNIT}')
    state = ssh(HOST, query)
    if state != 'active':
        raise RuntimeError(f'{UNIT} is {state}; see ~/.local/state/team4-lab5/service.log on the Pi')


# Returns the recorded session, opening the wheel GUI only when this session has none alive.
def start(root, course):
    if not (course / 'proxy_gui.py').is_file():
        raise RuntimeError(f'Course proxy missing: {course}')
    ensure_service()
    state = load_state(root)
    if state and proxy_alive(state['proxy']):
        return state
    stop(root)
    ensure_ghub()
    discover = "import os,json; print(json.dumps(dict(pi=os.environ['SSH_CONNECTION'].split()[2])))"
    pi_address = str(ipaddress.IPv4Address(json.loads(ssh(HOST, 'python3 -c ' + shlex.quote(discover)))['pi']))
    directory = root / 'logs/lab5/session' / time.strftime('%Y%m%d-%H%M%S')
    directory.mkdir(parents=True)
    proxy = launch_proxy(root, course, pi_address, directory / 'ready.json', directory / 'proxy.log',
                         extra=['--lab5'])
    state = {'proxy': proxy, 'pi': pi_address, 'log_directory': str(directory)}
    (root / STATE).write_text(json.dumps(state, indent=2), encoding='utf-8')
    LOG.info('Started wheel GUI %s; logs %s', proxy, directory)
    return state


# Latest complete STATUS line from the running cockpit, which appends to this log continuously.
def pi_status():
    lines = ssh(HOST, 'tail -c 20000 ~/.local/state/team4-lab5/service.log').splitlines()
    for line in reversed(lines):
        if line.startswith('STATUS '):
            try:
                return json.loads(line[7:])
            except json.JSONDecodeError:
                continue  # the newest line was still being written
    raise RuntimeError('No STATUS line in the Pi service log')


# What stands between the cluster and a healthy checkoff start; empty means ready.
def problems(status):
    raft = status['raft']
    found = []
    if not status['udp_ok']:
        found.append('no wheel input reaching the Pi')
    found += [f'{name} is not alive on CAN' for name in ('N2', 'N3') if not status['alive'].get(name)]
    if not raft['leader']:
        found.append('no Raft leader')
    if raft['nodes'] != 7:
        found.append(f"committed node set is {raft['nodes']:#x}, not 0x7")
    if raft['links'] != 63:
        found.append(f"committed CAN links are {raft['links']:#x}, not all six (0x3f)")
    if status['error']:
        found.append('cockpit is in ERROR')
    return found


def report(status):
    raft = status['raft']
    found = problems(status)
    head = 'READY' if not found else 'NOT READY: ' + '; '.join(found)
    return (f"{head}\nleader N{raft['leader']}, term {raft['term']}, commit {raft['commit']}, "
            f"nodes {raft['nodes']:#x}, links {raft['links']:#x}")


# With pythonw there is no console, so the result goes to a message box on Windows.
def tell(message, failed):
    stream = sys.stderr if failed else sys.stdout
    if stream:
        print(message, file=stream)
    elif os.name == 'nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'Lab 5 session', 0x10 if failed else 0x40)


def main(action):
    parser = argparse.ArgumentParser(description='Start/stop the Lab 5 wheel GUI and check the cluster. '
                                     'Start connects the wheel; keep hands clear and pedals released.')
    if action == 'start':
        parser.add_argument('--course-repo', type=Path, default=Path(
            os.environ.get('LOGITECH_WHEEL_REPO', REPO.parent / 'logitech-wheel-dev-updated-f26')))
        parser.add_argument('--restart', action='store_true', help='Close and reopen the wheel GUI')
    args = parser.parse_args()
    directory = REPO / 'logs/lab5/session'
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=directory / 'launcher.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    try:
        with session_lock(REPO):
            if action == 'stop' or args.restart:
                stop(REPO)
            if action == 'stop':
                tell('Wheel GUI stopped. The Pi cockpit service keeps running.', False)
                return 0
            state = start(REPO, args.course_repo.resolve())
            # Wheel input and the committed cockpit flag take a moment to settle.
            deadline = time.monotonic() + 10
            status = pi_status()
            while problems(status) and time.monotonic() < deadline:
                time.sleep(0.5)
                status = pi_status()
        message = report(status) + '\nLogs: ' + state['log_directory']
        LOG.info(message.replace('\n', ' | '))
        tell(message, bool(problems(status)))
        return 1 if problems(status) else 0
    except Exception as exc:
        LOG.exception('%s failed', action)
        tell(f'{action.capitalize()} failed: {exc}\nDetails: {directory / "launcher.log"}', True)
        return 1
