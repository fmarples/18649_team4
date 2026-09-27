"""Own one wheel GUI and one Pi bridge; never stop processes by runtime name."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import ipaddress
import json
import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import uuid

import psutil

LOG = logging.getLogger(__name__)


# Child programs must not create terminal windows; the wheel GUI is still visible.
def background_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}


# Use native Windows OpenSSH so the user's config/keys work outside Git Bash too.
def ssh(host, command):
    executable = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'System32/OpenSSH/ssh.exe' if os.name == 'nt' else Path(shutil.which('ssh') or 'ssh')
    result = subprocess.run([str(executable), '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                             '-o', 'StrictHostKeyChecking=yes', host, command],
                            capture_output=True, text=True, encoding='utf-8', timeout=25,
                            **background_options())
    if result.returncode:
        raise RuntimeError(f'SSH {host}: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout.strip()


# A per-repo lock serializes double clicks and stop/restart requests, without a server.
@contextmanager
def session_lock(root):
    directory = root / 'logs/session'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'session.lock').open('a+b') as lock:
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            if lock.read(1) == b'':
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def save_state(root, state):
    path = root / 'logs/session/state.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2), encoding='utf-8')
    temporary.replace(path)


# Check creation time as well as PID so a stale state file cannot target a reused PID.
def proxy_alive(identity):
    try:
        process = psutil.Process(identity['pid'])
        return process.create_time() == identity['created'] and process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def stop_proxy(identity):
    if not proxy_alive(identity):
        return
    process = psutil.Process(identity['pid'])
    owned = process.children(recursive=True) + [process]
    for child in owned:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(owned, timeout=5)
    for child in remaining:
        child.kill()
    _, remaining = psutil.wait_procs(remaining, timeout=5)
    if remaining:
        raise RuntimeError('Owned wheel GUI processes did not exit')


# G HUB is shared driver software. Start it if installed, but never stop it here.
def ensure_ghub():
    if os.name != 'nt':
        return
    if any(p.info['name'].lower() == 'lghub.exe' for p in psutil.process_iter(['name']) if p.info['name']):
        return
    executable = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LGHUB/lghub.exe'
    if not executable.is_file():
        raise RuntimeError('Install Logitech G HUB before starting the wheel')
    subprocess.Popen([str(executable)], **background_options())


# A ready file comes from the GUI only after the SDK reports a connected wheel.
def launch_proxy(root, course, pi_address, ready, console):
    interpreter = course / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not interpreter.is_file():
        raise RuntimeError(f'Course proxy Python environment missing: {interpreter}')
    env = os.environ.copy()
    env['LOGITECH_WHEEL_REPO'] = str(course)
    with console.open('a', encoding='utf-8') as log:
        process = subprocess.Popen([str(interpreter), '-u', '-X', 'faulthandler',
                                    str(root / 'windows/start_wheel_proxy.py'), '--pi', pi_address,
                                    '--connect', '--ready-file', str(ready)],
                                   cwd=course, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, **background_options())
    identity = {'pid': process.pid, 'created': psutil.Process(process.pid).create_time()}
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Wheel GUI exited ({process.returncode}); see {console}')
            if ready.exists():
                report = json.loads(ready.read_text(encoding='utf-8'))
                # Windows venv python.exe is a redirector that owns the real Python child.
                owned_pids = {process.pid} | {p.pid for p in psutil.Process(process.pid).children(recursive=True)}
                if report.get('pid') in owned_pids and report.get('connected') is True:
                    return identity
            time.sleep(0.1)
        raise RuntimeError(f'Wheel did not connect within 20 seconds; see {console}')
    except BaseException:
        stop_proxy(identity)
        raise


# Stop only the GUI identity and uniquely named systemd unit recorded by this launcher.
def stop(root):
    path = root / 'logs/session/state.json'
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding='utf-8'))
    errors = []
    if state.get('proxy'):
        try:
            stop_proxy(state['proxy'])
        except Exception as exc:
            errors.append(str(exc))
    if state.get('unit'):
        try:
            # --collect removes an exited unit. Absence therefore means already stopped.
            command = 'unit=' + shlex.quote(state['unit']) + '; if systemctl --user show "$unit" -p LoadState --value | grep -qx not-found; then exit 0; fi; systemctl --user stop "$unit"'
            ssh(state['host'], command)
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        raise RuntimeError('; '.join(errors) + '. Session state retained for a later stop retry.')
    path.unlink()
    LOG.info('Stopped session %s', state['unit'])


# Start existing Pi code without deploying files or touching the STM32 firmware.
def start(root, host, course):
    if not (course / 'proxy_gui.py').is_file():
        raise RuntimeError(f'Course proxy missing: {course}')
    path = root / 'logs/session/state.json'
    if path.exists():
        state = json.loads(path.read_text(encoding='utf-8'))
        if state.get('status') == 'running' and state.get('proxy') and proxy_alive(state['proxy']):
            if ssh(state['host'], 'systemctl --user show -p ActiveState --value ' + shlex.quote(state['unit'])) == 'active':
                return state
        stop(root)
    ensure_ghub()
    discover = "import os,json; p=os.environ['SSH_CONNECTION'].split(); print(json.dumps(dict(local=p[0],pi=p[2],home=os.path.expanduser('~'))))"
    network = json.loads(ssh(host, 'python3 -c ' + shlex.quote(discover)))
    pi_address = str(ipaddress.IPv4Address(network['pi']))
    local_address = str(ipaddress.IPv4Address(network['local']))
    token = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8]
    directory = root / 'logs/session' / token
    directory.mkdir(parents=True)
    remote_directory = network['home'] + '/18649/part2'
    remote_log = remote_directory + '/logs/session-' + token
    unit = 'lab2-wheel-' + token + '.service'
    state = {'host': host, 'unit': unit, 'pi': pi_address, 'local': local_address,
             'remote_log': remote_log, 'log_directory': str(directory), 'status': 'starting'}
    save_state(root, state)
    try:
        # Unique unit ownership makes rollback safe even if SSH drops during startup.
        args = ['systemd-run', '--user', '--unit=' + unit, '--collect',
                '--property=WorkingDirectory=' + remote_directory,
                '--property=StandardOutput=append:' + remote_log + '.console.log',
                '--property=StandardError=append:' + remote_log + '.console.log',
                '--property=KillSignal=SIGINT', '--property=TimeoutStopSec=5',
                'python3', '-u', '-X', 'faulthandler', remote_directory + '/part2_bridge.py',
                '--mode', 'live', '--sender', local_address, '--log', remote_log + '.csv']
        ssh(host, 'mkdir -p ' + shlex.quote(remote_directory + '/logs') + '; ' + shlex.join(args))
        time.sleep(0.6)
        active = ssh(host, 'systemctl --user show -p ActiveState --value ' + shlex.quote(unit))
        output = ssh(host, 'tail -c 12000 ' + shlex.quote(remote_log + '.console.log'))
        if active != 'active' or 'UART=' not in output:
            raise RuntimeError('Pi bridge did not initialize: ' + output)
        state['proxy'] = launch_proxy(root, course, pi_address, directory / 'ready.json', directory / 'proxy.log')
        state['status'] = 'running'
        save_state(root, state)
        LOG.info('Started %s; local logs %s; Pi logs %s', unit, directory, remote_log)
        return state
    except BaseException:
        LOG.exception('Session startup failed')
        if state.get('proxy'):
            stop_proxy(state['proxy'])
        try:
            stop(root)
        except Exception:
            LOG.exception('Rollback incomplete; use stop.py to retry')
        raise


def main(action):
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description='Start/stop the wheel GUI and Pi bridge. Start can move the wheel/car; keep hands clear and pedals released.')
    if action == 'start':
        parser.add_argument('--host', default='wheelpi', help='SSH config alias, default wheelpi')
        parser.add_argument('--course-repo', type=Path, default=Path(os.environ.get('LOGITECH_WHEEL_REPO', root.parent / 'logitech-wheel-dev-updated-f26')))
        parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    directory = root / 'logs/session'
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=directory / 'launcher.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    try:
        with session_lock(root):
            if action == 'stop' or args.restart:
                stop(root)
            if action == 'start':
                state = start(root, args.host, args.course_repo.resolve())
                if sys.stdout:
                    print('Running. Logs: ' + state['log_directory'])
    except Exception as exc:
        LOG.exception('%s failed', action)
        message = f'{action.capitalize()} failed: {exc}\nDetails: {directory / "launcher.log"}'
        if sys.stderr:
            print(message, file=sys.stderr)
        elif os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'Lab 2 wheel session', 0x10)
        return 1
    return 0
