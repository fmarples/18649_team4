"""Multilayer DC mesh of the saved Pi/+5V copper, not a thermal/AC qualification.

Extract with KiCad Python; solve with Python containing NumPy/SciPy/Shapely.
No CAD is edited. A square-cell sheet and four-sector plated-barrel model
include parallel routes and pad spreading omitted by the earlier tree screen.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(path, board_path):
    import pcbnew as p
    board = p.LoadBoard(str(board_path))
    allocation = json.loads((ROOT / 'Load-allocation-check.json').read_text())
    assert allocation['source_sha256'] == sha(ROOT / 'KiCad/Lab4.kicad_pcb')
    rail = allocation['five_volt']
    layers = [p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu]
    names = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
    pads = {(f.GetReference(), a.GetNumber()): a for f in board.GetFootprints() for a in f.Pads()}
    items = [a for a in pads.values() if a.GetNetname() == rail['net']]
    items += [a for a in board.GetTracks() if a.GetNetname() == rail['net']]
    def xy(q): return [p.ToMM(q.x), p.ToMM(q.y)]
    def polygon(item, layer):
        poly = p.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(poly, layer, 0, p.FromMM(.001), p.ERROR_INSIDE)
        def chain(c): return [xy(c.CPoint(i)) for i in range(c.PointCount())]
        return [{'outline': chain(poly.Outline(i)),
                 'holes': [chain(poly.Hole(i, j)) for j in range(poly.HoleCount(i))]}
                for i in range(poly.OutlineCount())]
    copper = {name: [] for name in names}
    for zone in board.Zones():
        if zone.GetIsRuleArea() or zone.GetNetname() != rail['net']: continue
        for layer, name in zip(layers, names):
            if not zone.IsOnLayer(layer): continue
            filled=zone.GetFilledPolysList(layer)
            def chain(c): return [xy(c.CPoint(k)) for k in range(c.PointCount())]
            copper[name].extend({'outline':chain(filled.Outline(k)),
                'holes':[chain(filled.Hole(k,j)) for j in range(filled.HoleCount(k))]}
                for k in range(filled.OutlineCount()))
    barrels = []
    for item in items:
        active = [i for i, layer in enumerate(layers) if item.IsOnLayer(layer)]
        for i in active: copper[names[i]].extend(polygon(item, layers[i]))
        if item.Type() == p.PCB_VIA_T:
            drill = p.ToMM(item.GetDrill())
        elif item.Type() == p.PCB_PAD_T and item.GetAttribute() == p.PAD_ATTRIB_PTH:
            size = xy(item.GetDrillSize())
            assert abs(size[0]-size[1]) < 1e-6, 'Add slotted-barrel geometry before using this model'
            drill = size[0]
        else:
            continue
        barrels.append({'xy': xy(item.GetPosition()), 'drill_mm': drill, 'layers': active})
    ports = {}
    # The Pi is below the PCB; its socket lead terminates at the back pad.
    for ref, pin in [('L2', '2')] + [(x['ref'], x['pin']) for x in rail['loads']]:
        a = pads[(ref, pin)]
        layer_index = 3 if ref == 'J70' else (0 if a.IsOnLayer(p.F_Cu) else 3)
        ports[ref] = {'pin': pin, 'layer': layer_index,
                      'xy': xy(a.GetPosition()), 'polygons': polygon(a, layers[layer_index])}
    result = {'board_sha256': sha(board_path),
              'allocation_sha256': sha(ROOT / 'Load-allocation-check.json'),
              'rail': rail, 'layers': names, 'copper': copper,
              'barrels': barrels, 'ports': ports,
              'thickness_mm': [.035, .0152, .0152, .035],
              'layer_centers_mm': [.0175, .2530, 1.3332, 1.5687]}
    path.write_text(json.dumps(result), encoding='utf-8')
    print(f'Extracted {len(items)} copper items and {len(barrels)} plated barrels', flush=True)


def network_solve(n, edges, conductance, current):
    import numpy as np
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse.linalg import spsolve
    edges = np.asarray(edges, dtype=int); g = np.asarray(conductance)
    a, b = edges.T
    matrix = sparse.coo_matrix((np.r_[g,g,-g,-g], (np.r_[a,b,a,b], np.r_[a,b,b,a])), shape=(n,n)).tocsr()
    count, labels = connected_components(matrix, directed=False)
    energized = set(labels[np.abs(current) > 1e-15])
    if len(energized) != 1:
        raise ValueError(f'Mesh disconnects energized copper into {len(energized)} islands')
    selected = np.flatnonzero(labels == next(iter(energized)))
    if abs(current.sum()) > 1e-10: raise ValueError('Unbalanced source/sink currents')
    reduced = selected[1:]
    voltage = np.zeros(n)
    voltage[reduced] = spsolve(matrix[reduced][:,reduced], current[reduced])
    residual = matrix @ voltage - current
    heat = float(np.sum(g*(voltage[a]-voltage[b])**2))
    work = float(current @ voltage)
    if np.max(np.abs(residual)) > 1e-6 or abs(heat-work) > 1e-7:
        raise ArithmeticError('KCL or power balance failed')
    return voltage, {'max_KCL_residual_A': float(np.max(np.abs(residual))),
                     'copper_loss_W': heat, 'source_work_W': work,
                     'unenergized_islands': int(count-1)}


def solve(path, output, steps, board_path):
    import numpy as np
    import shapely
    from shapely.geometry import Polygon, Point
    from scipy.spatial import cKDTree
    data = json.loads(path.read_text())
    assert data['board_sha256'] == sha(board_path)
    assert data['allocation_sha256'] == sha(ROOT / 'Load-allocation-check.json')
    def poly(parts):
        return shapely.unary_union([shapely.make_valid(Polygon(c['outline'], c['holes'])) for c in parts])
    holes = shapely.unary_union([Point(*b['xy']).buffer(b['drill_mm']/2, quad_segs=48) for b in data['barrels']])
    shapes = [poly(data['copper'][name]).difference(holes) for name in data['layers']]
    for s in shapes: shapely.prepare(s)
    rho = 1.72e-5  # ohm mm, approximately 20 C
    results = []
    for step in steps:
        coords=[]; maps=[]; trees=[]; offsets=[]; edges=[]; gs=[]; offset=0
        for i, shape in enumerate(shapes):
            if shape.is_empty:
                coords.append(np.empty((0,2))); maps.append(None); trees.append(None); offsets.append(offset); continue
            x0,y0,x1,y1=shape.bounds
            xs=np.arange(math.floor(x0/step)*step+step/2,x1,step)
            ys=np.arange(math.floor(y0/step)*step+step/2,y1,step)
            xx,yy=np.meshgrid(xs,ys)
            mask=shapely.contains_xy(shape,xx,yy)
            xy=np.c_[xx[mask],yy[mask]]
            ids=np.full(mask.shape,-1,dtype=np.int32); ids[mask]=np.arange(len(xy))+offset
            for dy,dx in [(0,1),(1,0)]:
                a=(slice(None,-dy or None),slice(None,-dx or None)); b=(slice(dy,None),slice(dx,None))
                valid=mask[a]&mask[b]
                for t in [.25,.5,.75]: valid &= shapely.contains_xy(shape,xx[a]+dx*step*t,yy[a]+dy*step*t)
                e=np.c_[ids[a][valid],ids[b][valid]]
                edges.append(e); gs.append(np.full(len(e),data['thickness_mm'][i]/rho))
            coords.append(xy); maps.append(ids); trees.append(cKDTree(xy)); offsets.append(offset); offset+=len(xy)
        max_projection=0.
        for barrel in data['barrels']:
            radius=barrel['drill_mm']/2+.04
            area=math.pi*((barrel['drill_mm']+.04)**2-barrel['drill_mm']**2)/4  # assumed 20 um plating
            for ia,ib in zip(barrel['layers'],barrel['layers'][1:]):
                distance=data['layer_centers_mm'][ib]-data['layer_centers_mm'][ia]
                r=rho*distance/area
                for theta in [0,math.pi/2,math.pi,3*math.pi/2]:
                    point=np.array(barrel['xy'])+radius*np.array([math.cos(theta),math.sin(theta)])
                    da,a=trees[ia].query(point); db,b=trees[ib].query(point)
                    max_projection=max(max_projection,float(da),float(db))
                    if max(da,db)>step*1.6: raise ValueError('Barrel site missed its copper land')
                    edges.append(np.array([[a+offsets[ia],b+offsets[ib]]])); gs.append(np.array([1/(4*r)]))
        port_ids={}
        for ref,port in data['ports'].items():
            i=port['layer']; s=poly(port['polygons']).difference(holes)
            chosen=np.flatnonzero(shapely.contains_xy(s,coords[i][:,0],coords[i][:,1]))+offsets[i]
            if not len(chosen): raise ValueError(f'No nodes at {ref}; refine mesh')
            port_ids[ref]=chosen
        current=np.zeros(offset)
        for load in data['rail']['loads']:
            ids=port_ids[load['ref']]; current[ids]-=load['allocation_A']/len(ids)
        src=port_ids['L2']; current[src]+=-current.sum()/len(src)
        edge=np.concatenate(edges); conductance=np.concatenate(gs)
        voltage,checks=network_solve(offset,edge,conductance,current)
        source=float(voltage[src].mean())
        drops={ref:source-float(voltage[ids].mean()) for ref,ids in port_ids.items() if ref!='L2'}
        result={'mesh_mm':step,'nodes':offset,'edges':len(edge),'barrel_site_max_projection_mm':max_projection,
                'positive_feed_drop_V':drops,**checks}
        results.append(result)
        print(f'{step:g} mm: {offset} nodes; Pi drop {drops["J70"]*1000:.3f} mV',flush=True)
    output.write_text(json.dumps({'board_sha256':data['board_sha256'],'allocation_sha256':data['allocation_sha256'],
        'fabrication_release':False,'method':'Square-cell multilayer DC mesh; four-sector 20 um plated barrels; uniform current over component pad areas',
        'assumptions':{'copper_resistivity_ohm_mm':rho,'layer_thickness_mm':data['thickness_mm'],
                       'barrel_plating_mm':.020,'Pi_current_A':next(x['allocation_A'] for x in data['rail']['loads'] if x['ref']=='J70')},
        'omits':['Regulator accuracy and transient response','Connector resistance','Component and socket lead resistance','Ground return','Temperature rise and copper hot resistance','AC impedance and current crowding below mesh scale'],
        'results':results},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['extract','solve'])
    parser.add_argument('--geometry',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'Pi-feed-mesh-check.json')
    parser.add_argument('--steps',type=float,nargs='+',default=[.1,.05])
    parser.add_argument('--board',type=Path,default=ROOT/'KiCad/Lab4.kicad_pcb')
    args=parser.parse_args()
    if args.mode=='extract': extract(args.geometry,args.board)
    else: solve(args.geometry,args.output,args.steps,args.board)
