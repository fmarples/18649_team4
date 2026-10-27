"""DC resistor-sheet solver. Requires NumPy and SciPy; no KiCad dependency."""
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu


class Sheet:
    """One resistor rho/thickness between adjacent equal square mesh cells.

    Edges must already exclude copper voids. Sources are distributed currents,
    not equipotential metal electrodes. Fixing one node only chooses a voltage
    reference; every case must explicitly balance injected and extracted current.
    """

    def __init__(self, node_count, edges, resistance_per_square):
        self.n = node_count
        self.edges = np.asarray(edges, dtype=int)
        a, b = self.edges.T
        graph = sparse.coo_matrix((np.ones(len(a)), (a, b)), shape=(self.n, self.n))
        components, _ = connected_components(graph, directed=False)
        if components != 1:
            raise ValueError(f"mesh has {components} disconnected components")
        g = np.full(len(a), 1 / resistance_per_square)
        self.matrix = sparse.coo_matrix(
            (np.r_[g, g, -g, -g], (np.r_[a, b, a, b], np.r_[a, b, b, a])),
            shape=(self.n, self.n)).tocsr()
        self.factor = splu(self.matrix[1:, 1:].tocsc())
        self.r = resistance_per_square

    def solve(self, current):
        current = np.asarray(current, dtype=float)
        if abs(current.sum()) > 1e-10:
            raise ValueError("current injections must sum to zero")
        voltage = np.r_[0., self.factor.solve(current[1:])]
        residual = self.matrix @ voltage - current
        a, b = self.edges.T
        heat = float(np.sum((voltage[a] - voltage[b])**2 / self.r))
        work = float(current @ voltage)
        if np.max(np.abs(residual)) > 1e-7 or abs(heat - work) > 1e-8:
            raise ArithmeticError("KCL or power balance failed")
        return voltage, {"max_KCL_residual_A": float(np.max(np.abs(residual))),
                         "sheet_loss_W": heat, "source_work_W": work}


def rectangle_edges(nx, ny):
    grid = np.arange(nx * ny).reshape(ny, nx)
    return np.concatenate((np.c_[grid[:, :-1].ravel(), grid[:, 1:].ravel()],
                           np.c_[grid[:-1].ravel(), grid[1:].ravel()]))
