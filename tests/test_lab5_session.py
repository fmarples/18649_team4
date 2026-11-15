"""Exercise the Lab 5 session lifecycle with SSH, sudo and GUI boundaries replaced."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_session():
    spec = importlib.util.spec_from_file_location('lab5_session', ROOT / 'lab5/session.py')
    session = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(session)
    return session


def course_in(root):
    course = root / 'course'
    course.mkdir()
    (course / 'proxy_gui.py').write_text('')
    return course


class Lab5SessionTests(unittest.TestCase):
    def test_start_opens_one_lab5_proxy_and_stop_leaves_the_pi_service_running(self):
        session = load_session()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            course = course_in(root)
            calls = []

            def ssh(host, command):
                calls.append(command)
                if 'SSH_CONNECTION' in command:
                    return json.dumps({'pi': '172.26.166.33'})
                if 'is-active' in command:
                    return 'active'
                return ''

            with patch.object(session, 'ssh', side_effect=ssh), \
                 patch.object(session, 'launch_proxy', return_value={'pid': 321, 'created': 123.0}) as launch, \
                 patch.object(session, 'stop_proxy') as stop_proxy, \
                 patch.object(session, 'proxy_alive', return_value=True), \
                 patch.object(session, 'sudo') as sudo, \
                 patch.object(session, 'ensure_ghub'):
                state = session.start(root, course)
                self.assertEqual(state['proxy'], {'pid': 321, 'created': 123.0})
                self.assertEqual(launch.call_args.args[2], '172.26.166.33')
                self.assertEqual(launch.call_args.kwargs['extra'], ['--lab5'])
                self.assertEqual(session.start(root, course)['proxy'], state['proxy'])
                launch.assert_called_once()
                sudo.assert_not_called()
                session.stop(root)
                stop_proxy.assert_called_once_with(state['proxy'])
                self.assertFalse((root / 'logs/lab5/session/state.json').exists())
            self.assertFalse(any('stop' in command or 'disable' in command for command in calls))

    def test_start_restarts_a_stopped_pi_service_and_fails_if_it_stays_down(self):
        session = load_session()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            course = course_in(root)
            active = iter(['inactive', 'active', 'failed', 'failed'])

            def ssh(host, command):
                if 'SSH_CONNECTION' in command:
                    return json.dumps({'pi': '172.26.166.33'})
                return next(active) if 'is-active' in command else ''

            with patch.object(session, 'ssh', side_effect=ssh), \
                 patch.object(session, 'launch_proxy', return_value={'pid': 321, 'created': 123.0}) as launch, \
                 patch.object(session, 'proxy_alive', return_value=False), \
                 patch.object(session, 'stop_proxy'), \
                 patch.object(session, 'sudo_password', return_value='secret'), \
                 patch.object(session, 'sudo') as sudo, \
                 patch.object(session, 'ensure_ghub'):
                session.start(root, course)
                sudo.assert_called_once_with('secret', 'systemctl start team4-lab5-cockpit.service')
                launch.assert_called_once()
                with self.assertRaisesRegex(RuntimeError, 'team4-lab5-cockpit.service is failed'):
                    session.start(root, course)
                launch.assert_called_once()

    def test_readiness_names_what_blocks_checkoff(self):
        session = load_session()
        healthy = {'error': False, 'udp_ok': True, 'alive': {'N2': True, 'N3': True},
                   'raft': {'nodes': 7, 'links': 63, 'leader': 1, 'term': 538, 'commit': 3751}}
        no_wheel = {**healthy, 'udp_ok': False, 'error': True}
        # tail cuts the first line, and the cockpit may be mid-write on the last one.
        tail = ('ue}\nPPS global_us=1\nSTATUS ' + json.dumps(no_wheel) + '\nSTATUS ' + json.dumps(healthy)
                + '\nSTATUS {"error": tr')
        with patch.object(session, 'ssh', return_value=tail):
            self.assertEqual(session.pi_status(), healthy)
        self.assertEqual(session.problems(healthy), [])
        self.assertIn('wheel input', ' '.join(session.problems(no_wheel)))
        n3_down = {**healthy, 'error': True, 'alive': {'N2': True, 'N3': False},
                   'raft': {**healthy['raft'], 'nodes': 3}}
        self.assertIn('N3', ' '.join(session.problems(n3_down)))
        link_cut = {**healthy, 'raft': {**healthy['raft'], 'links': 61}}
        self.assertIn('link', ' '.join(session.problems(link_cut)))


if __name__ == '__main__':
    unittest.main()
