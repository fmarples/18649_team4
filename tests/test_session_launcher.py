"""Exercise the public session lifecycle with SSH and GUI hardware boundaries replaced."""
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import venv
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_session():
    spec = importlib.util.spec_from_file_location('wheel_session', ROOT / 'tools/wheel_session.py')
    session = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(session)
    return session


class SessionLauncherTests(unittest.TestCase):
    def test_start_owns_both_processes_and_stop_targets_only_that_session(self):
        session = load_session()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            course = root / 'course'
            course.mkdir()
            (course / 'proxy_gui.py').write_text('')
            (root / 'windows').mkdir()
            (root / 'windows/start_wheel_proxy.py').write_text('')
            calls = []

            def ssh(host, command):
                calls.append((host, command))
                if 'SSH_CONNECTION' in command:
                    return json.dumps({'pi': '172.26.166.33', 'local': '172.26.88.86', 'home': '/home/labuser'})
                if 'ActiveState' in command:
                    return 'active'
                if 'tail ' in command:
                    return 'LINK-ONLY mode=live; UART=/dev/serial0\n'
                return ''

            with patch.object(session, 'ssh', side_effect=ssh), \
                 patch.object(session, 'launch_proxy', return_value={'pid': 321, 'created': 123.0}), \
                 patch.object(session, 'stop_proxy') as stop_proxy, \
                 patch.object(session, 'proxy_alive', return_value=True), \
                 patch.object(session, 'ensure_ghub'):
                state = session.start(root, 'wheelpi', course)
                self.assertEqual(state['host'], 'wheelpi')
                self.assertEqual(state['proxy']['pid'], 321)
                self.assertEqual(state['status'], 'running')
                self.assertTrue(any('systemd-run' in command and '--mode live' in command for _, command in calls))
                before = len(calls)
                self.assertEqual(session.start(root, 'wheelpi', course)['unit'], state['unit'])
                self.assertFalse(any('systemd-run' in command for _, command in calls[before:]))
                session.stop(root)
                stop_proxy.assert_called_once_with(state['proxy'])
                self.assertTrue(any(' stop ' in command and state['unit'] in command for _, command in calls))
                self.assertFalse((root / 'logs/session/state.json').exists())

    def test_ready_signal_from_venv_python_child_is_accepted(self):
        session = load_session()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            course = root / 'course'
            venv.EnvBuilder(with_pip=False).create(course / '.venv')
            (root / 'windows').mkdir()
            (root / 'windows/start_wheel_proxy.py').write_text(
                'import json,os,pathlib,sys,time\n'
                'path=pathlib.Path(sys.argv[sys.argv.index("--ready-file")+1])\n'
                'path.write_text(json.dumps(dict(pid=os.getpid(),connected=True)))\n'
                'time.sleep(60)\n', encoding='utf-8')
            identity = session.launch_proxy(root, course, '127.0.0.1', root / 'ready.json', root / 'proxy.log')
            try:
                self.assertTrue(session.proxy_alive(identity))
                ready_pid = json.loads((root / 'ready.json').read_text())['pid']
                self.assertTrue(session.psutil.pid_exists(ready_pid))
            finally:
                session.stop_proxy(identity)
            self.assertFalse(session.proxy_alive(identity))
            self.assertFalse(session.psutil.pid_exists(ready_pid))

    def test_stale_pid_does_not_kill_an_unrelated_process(self):
        session = load_session()
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            created = session.psutil.Process(child.pid).create_time()
            session.stop_proxy({'pid': child.pid, 'created': created - 100})
            self.assertIsNone(child.poll())
            session.stop_proxy({'pid': child.pid, 'created': created})
            self.assertIsNotNone(child.poll())
        finally:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)

    def test_failed_remote_stop_preserves_retry_state_but_stops_local_gui(self):
        session = load_session()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'logs/session').mkdir(parents=True)
            state = {'host': 'wheelpi', 'unit': 'lab2-wheel-owned.service', 'proxy': {'pid': 123, 'created': 1}}
            session.save_state(root, state)
            with patch.object(session, 'ssh', side_effect=RuntimeError('Pi unreachable')), \
                 patch.object(session, 'stop_proxy') as stop_proxy:
                with self.assertRaisesRegex(RuntimeError, 'state retained'):
                    session.stop(root)
                stop_proxy.assert_called_once_with(state['proxy'])
                self.assertTrue((root / 'logs/session/state.json').exists())

    def test_gui_failure_rolls_back_only_the_new_remote_unit(self):
        session = load_session()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'proxy_gui.py').write_text('')
            calls = []
            def ssh(host, command):
                calls.append(command)
                if 'SSH_CONNECTION' in command:
                    return json.dumps({'pi': '172.26.166.33', 'local': '172.26.88.86', 'home': '/home/labuser'})
                if 'ActiveState' in command:
                    return 'active'
                if 'tail ' in command:
                    return 'mode=live UART=/dev/serial0'
                return ''
            with patch.object(session, 'ssh', side_effect=ssh), \
                 patch.object(session, 'ensure_ghub'), \
                 patch.object(session, 'launch_proxy', side_effect=RuntimeError('No wheel')):
                with self.assertRaisesRegex(RuntimeError, 'No wheel'):
                    session.start(root, 'wheelpi', root)
            self.assertFalse((root / 'logs/session/state.json').exists())
            self.assertEqual(len([cmd for cmd in calls if 'systemd-run' in cmd]), 1)
            self.assertEqual(len([cmd for cmd in calls if ' stop ' in cmd]), 1)
            self.assertFalse(any('pkill' in cmd or 'killall' in cmd for cmd in calls))


if __name__ == '__main__':
    unittest.main()
