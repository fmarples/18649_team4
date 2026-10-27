"""Analytical checks independent of the Lab 4 board geometry."""
import unittest
import numpy as np
from ground_sheet import Sheet, rectangle_edges


class SheetTests(unittest.TestCase):
    def test_rectangle_squares_and_current_scaling(self):
        nx, ny, resistance = 21, 8, .002
        sheet = Sheet(nx * ny, rectangle_edges(nx, ny), resistance)
        i = np.zeros((ny, nx)); i[:, 0] = 3 / ny; i[:, -1] = -3 / ny
        v, _ = sheet.solve(i.ravel()); v = v.reshape(ny, nx)
        # ny parallel chains, each with nx-1 resistors.
        self.assertAlmostEqual(float((v[:, 0] - v[:, -1]).mean()),
                               3 * resistance * (nx - 1) / ny, places=11)
        v2, _ = sheet.solve(2 * i.ravel())
        np.testing.assert_allclose(v2, 2 * v.ravel(), atol=1e-12)

    def test_resistivity_and_thickness_scaling(self):
        edges = rectangle_edges(5, 4)
        i = np.zeros(20); i[0] = 1; i[-1] = -1
        a, _ = Sheet(20, edges, .001).solve(i)
        b, _ = Sheet(20, edges, .002).solve(i)
        np.testing.assert_allclose(b, 2 * a, atol=1e-12)

    def test_slot_increases_resistance(self):
        edges = rectangle_edges(7, 7)
        # Barrier between columns 2/3, with one bridge in the last row.
        cut = [e for e in edges if not (e[1] - e[0] == 1 and
                                       e[0] % 7 == 2 and e[0] // 7 < 6)]
        i = np.zeros(49); i[0] = 1; i[6] = -1
        a, _ = Sheet(49, edges, .001).solve(i)
        b, _ = Sheet(49, cut, .001).solve(i)
        self.assertGreater(b[0] - b[6], a[0] - a[6])

    def test_disconnected_and_unbalanced_rejected(self):
        with self.assertRaises(ValueError):
            Sheet(4, [(0, 1), (2, 3)], .001)
        with self.assertRaises(ValueError):
            Sheet(4, rectangle_edges(2, 2), .001).solve([1, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
