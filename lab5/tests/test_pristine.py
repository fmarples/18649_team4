"""Ordering and refusal rules of the pristine reset, with fake nodes.

No probe, SSH or flash is touched; the erase and reset themselves need the
bench. What is checked here is that nothing is destroyed before every backup
exists, that the Nucleos stay halted until the Pi leads term 1, and that a
failure puts the cluster back on its feet.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pristine  # noqa: E402


def status(role=2, leader=1, term=1, failed=0, nodes=7, links=63, alive=True):
    return {'raft': {'role': role, 'leader': leader, 'term': term, 'failed': failed,
                     'nodes': nodes, 'links': links},
            'alive': {'N2': alive, 'N3': alive}, 'error': True, 'udp_ok': False}


class FakeNucleo:
    def __init__(self, node, calls, fail=None):
        self.node, self.calls, self.fail = node, calls, fail

    def __getattr__(self, step):
        def run(*_):
            self.calls.append(f'{self.node}.{step}')
            if step == self.fail:
                raise RuntimeError(f'{self.node} {step} failed')
        return run


class FakePi(FakeNucleo):
    def __init__(self, calls, fail=None, led=status()):
        super().__init__('pi', calls, fail)
        self.led = led

    def wait(self, problems, seconds):
        self.calls.append('pi.wait')
        return self.led


def run(fail_node=None, fail_step=None, led=status()):
    calls = []
    nucleos = [FakeNucleo(node, calls, fail_step if node == fail_node else None) for node in ('n2', 'n3')]
    pi = FakePi(calls, fail_step if fail_node == 'pi' else None, led)
    try:
        return calls, pristine.wipe(nucleos, pi, Path('unused')), None
    except RuntimeError as error:
        return calls, None, error


class WipeOrderTests(unittest.TestCase):
    def test_backs_up_everything_before_erasing_and_releases_nucleos_after_the_pi_leads(self):
        calls, result, error = run()
        self.assertIsNone(error)
        self.assertEqual(calls, [
            'pi.stop', 'n2.halt', 'n3.halt',
            'n2.backup', 'n3.backup', 'pi.backup',
            'n2.erase', 'n3.erase', 'pi.clear',
            'pi.start', 'pi.wait', 'n2.release', 'n3.release', 'pi.wait'])
        self.assertEqual(pristine.cold_start_problems(result), [])

    def test_failed_backup_destroys_nothing_and_restores_the_cluster(self):
        for node in ('n2', 'n3', 'pi'):
            calls, _, error = run(node, 'backup')
            self.assertIsNotNone(error)
            self.assertFalse([c for c in calls if c.endswith(('.erase', '.clear'))], calls)
            self.assertEqual(calls[-3:], ['pi.start', 'n2.release', 'n3.release'])

    def test_missing_nucleo_restarts_the_pi_without_erasing(self):
        calls, _, error = run('n3', 'halt')
        self.assertIsNotNone(error)
        self.assertEqual(calls, ['pi.stop', 'n2.halt', 'n3.halt', 'pi.start', 'n2.release', 'n3.release'])

    def test_pi_that_does_not_lead_term_one_is_reported(self):
        calls, _, error = run(led=status(role=0, leader=0))
        self.assertIn('Pi did not become the cold-start leader', str(error))
        self.assertEqual(calls[-2:], ['n2.release', 'n3.release'])


class ProblemTests(unittest.TestCase):
    def test_cold_start_requires_pi_leader_in_term_one_with_the_full_graph(self):
        self.assertEqual(pristine.cold_start_problems(status()), [])
        self.assertEqual(pristine.leader_problems(None), ['no STATUS line from the restarted cockpit'])
        # An election happened: a Nucleo leads a later term.
        self.assertEqual(len(pristine.leader_problems(status(role=0, leader=2, term=2))), 2)
        self.assertEqual(pristine.cold_start_problems(status(alive=False, nodes=1, links=3)), [
            'N2 is not alive on CAN', 'N3 is not alive on CAN',
            'committed node set is 0x1, not 0x7', 'committed CAN links are 0x3, not all six (0x3f)'])


if __name__ == '__main__':
    unittest.main()
