"""Independent circuit tests for the multilayer feed solver."""
import unittest
import numpy as np
from check_pi_feed import network_solve


class FeedTests(unittest.TestCase):
    def test_parallel_and_series_paths(self):
        # Two 0.02-ohm paths in parallel, then a 0.003-ohm barrel.
        edges=[(0,1),(0,1),(1,2)]
        v, result=network_solve(3,edges,[50,50,1/.003],np.array([3.,0.,-3.]))
        self.assertAlmostEqual(v[0]-v[2],3*(.01+.003),places=11)
        self.assertAlmostEqual(result['copper_loss_W'],9*(.01+.003),places=11)

    def test_square_strip_and_load_scaling(self):
        from ground_sheet import rectangle_edges
        nx,ny=21,8; edges=rectangle_edges(nx,ny); g=np.full(len(edges),1/.002)
        i=np.zeros((ny,nx)); i[:,0]=3/ny; i[:,-1]=-3/ny
        v,_=network_solve(nx*ny,edges,g,i.ravel())
        self.assertAlmostEqual(v[0]-v[nx-1],3*.002*(nx-1)/ny,places=10)
        v2,_=network_solve(nx*ny,edges,g,2*i.ravel())
        np.testing.assert_allclose(v2,2*v,atol=1e-10)

    def test_unused_island_is_ignored_but_active_disconnect_rejected(self):
        edges=[(0,1),(2,3)]
        v,r=network_solve(4,edges,[10,10],np.array([1.,-1.,0.,0.]))
        self.assertAlmostEqual(v[0]-v[1],.1)
        self.assertEqual(r['unenergized_islands'],1)
        with self.assertRaises(ValueError):
            network_solve(4,edges,[10,10],np.array([1.,0.,0.,-1.]))
        with self.assertRaises(ValueError):
            network_solve(2,[(0,1)],[10],np.array([1.,0.]))


if __name__=='__main__': unittest.main()
