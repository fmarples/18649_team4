import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_network import Network


class EventTests(unittest.TestCase):
    def setUp(self):
        self.n = Network()
        self.n.run(600)

    def tearDown(self):
        self.n.close()

    def test_n2_event_is_logged_on_all_nodes_in_hop(self):
        self.n.links -= {(1, 1), (3, 0)}
        self.n.run(500)
        self.assertTrue(self.n.nodes[2].event())
        self.n.run(600)
        for node in self.n.nodes.values():
            self.assertEqual([e for _, _, e in node.log()].count(22), 1)

    def test_events_held_while_pi_down_then_replayed_once(self):
        for node in self.n.nodes.values():
            list(node.applied())
        self.n.active.remove(1)
        self.n.run(600)
        for _ in range(3):
            self.assertTrue(self.n.nodes[2].event())
        self.n.run(600)
        leader = next(
            self.n.nodes[i] for i in (2, 3) if self.n.nodes[i].status["role"] == 2
        )
        self.assertEqual(leader.health(self.n.now)["held_events"], 3)
        self.n.active.add(1)
        self.n.run(1000)
        rows = list(self.n.nodes[1].applied())
        event_rows = [x for x in rows if x[2] == 22]
        self.assertEqual(len(event_rows), 3)
        self.assertTrue(all(x[3] for x in event_rows), event_rows)
        self.assertEqual([x[0] for x in rows], sorted(set(x[0] for x in rows)))
        self.assertTrue(self.n.nodes[2].event())
        self.n.run(300)
        live = [x for x in self.n.nodes[1].applied() if x[2] == 22]
        self.assertEqual(len(live), 1)
        self.assertFalse(live[0][3])
        self.assertEqual(leader.health(self.n.now)["held_events"], 0)

    def test_isolated_follower_does_not_inflate_terms(self):
        self.n.links -= {(3, 0), (3, 1)}
        self.n.run(3000)
        self.assertTrue(all(n.status["term"] == 1 for n in self.n.nodes.values()))
        self.n.links |= {(3, 0), (3, 1)}
        self.n.run(600)
        self.assertTrue(all(n.status["term"] == 1 for n in self.n.nodes.values()))

    def test_isolated_leader_changes_majority_term_once(self):
        self.n.links -= {(1, 0), (1, 1)}
        self.n.run(3000)
        self.assertEqual(self.n.nodes[2].status["term"], 2)
        self.assertEqual(self.n.nodes[3].status["term"], 2)
        self.n.links |= {(1, 0), (1, 1)}
        self.n.run(600)
        self.assertTrue(all(n.status["term"] == 2 for n in self.n.nodes.values()))


if __name__ == "__main__":
    unittest.main()
