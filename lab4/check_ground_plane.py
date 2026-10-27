"""Screen saved In1 ground-plane DC resistance; NOT a full return-path model.

Run with KiCad Python and --solver-python pointing to Python with NumPy/SciPy/Shapely.
Only temporary mesh files are created; the saved PCB is never modified.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def extract(destination):
    import numpy as np
    import pcbnew as p
    b = p.LoadBoard(str(ROOT / "KiCad/Lab4.kicad_pcb"))
    digest = hashlib.sha256((ROOT / "KiCad/Lab4.kicad_pcb").read_bytes()).hexdigest()
    allocation = json.loads((ROOT / "Load-allocation-check.json").read_text(encoding="utf-8"))
    assert allocation["source_sha256"] == digest, "refresh supply allocation first"
    planes = [z.GetFilledPolysList(p.In1_Cu) for z in b.Zones()
              if not z.GetIsRuleArea() and z.GetLayer() == p.In1_Cu and z.GetNetname() == "/GND"]
    assert len(planes) == 1
    plane = planes[0]
    def xy(q): return [p.ToMM(q.x), p.ToMM(q.y)]
    def inside(x, y): return plane.Contains(p.VECTOR2I(p.FromMM(float(x)), p.FromMM(float(y))))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    pads = {(f.GetReference(), a.GetNumber()): a for f in b.GetFootprints() for a in f.Pads()}
    sites = [(t.m_Uuid.AsString(), xy(t.GetPosition())) for t in b.GetTracks()
             if t.Type() == p.PCB_VIA_T and t.GetNetname() == "/GND"]
    sites += [(f"{r}.{n}", xy(a.GetPosition())) for (r, n), a in pads.items()
              if a.GetNetname() == "/GND" and a.GetAttribute() == p.PAD_ATTRIB_PTH]
    ports = {}
    def port(ref, explicit=None):
        if ref in ports: return ref
        candidates = ([pads[(ref, n)] for n in explicit] if explicit else
                      [a for a in fps[ref].Pads() if a.GetNetname() == "/GND"])
        # For tiny resistor loads, use their physical location as a local return
        # proxy; this does NOT assert that their other terminal is grounded.
        origin = [xy(a.GetPosition()) for a in candidates] or [xy(fps[ref].GetPosition())]
        selected = []
        for q in origin:
            site = min(sites, key=lambda s: math.dist(q, s[1]))
            selected.append(dict(id=site[0], xy_mm=site[1],
                                 projection_mm=math.dist(q, site[1])))
        unique = {s["id"]: s for s in selected}
        ports[ref] = dict(sites=list(unique.values()),
                          location_only_proxy=not bool(candidates),
                          ground_pads=[a.GetNumber() for a in candidates])
        return ref
    # Mode-select ground pins are not load-current return pins.
    for row in allocation["logic"]["loads"]:
        r = row["ref"]
        port(r, ["2"] if r in ["U11", "U15", "U21", "U25", "U31", "U35"] else None)
    for row in allocation["five_volt"]["loads"]: port(row["ref"])
    for r in ["U40", "U41", "U42", "R421", "R431", "J90", "J40"]: port(r)
    # Keep motor sense grounds distinct from the driver's logic ground.
    ports["motor_left"] = {"sites": [{"id": "U80.1", "xy_mm": xy(pads[("U80", "1")].GetPosition()), "projection_mm": 0.}], "ground_pads": ["1"], "location_only_proxy": False}
    ports["motor_right"] = {"sites": [{"id": "U80.15", "xy_mm": xy(pads[("U80", "15")].GetPosition()), "projection_mm": 0.}], "ground_pads": ["15"], "location_only_proxy": False}
    # Its 40mA logic allocation belongs at pin 8, not sense pins 1/15.
    del ports["U80"]; port("U80", ["8"])
    box = b.GetBoardEdgesBoundingBox()
    bounds = [math.floor(p.ToMM(box.GetLeft())), math.floor(p.ToMM(box.GetTop())),
              math.ceil(p.ToMM(box.GetRight())), math.ceil(p.ToMM(box.GetBottom()))]
    def points(chain): return [xy(chain.CPoint(i)) for i in range(chain.PointCount())]
    contours = [dict(outline=points(plane.Outline(i)),
                     holes=[points(plane.Hole(i, j)) for j in range(plane.HoleCount(i))])
                for i in range(plane.OutlineCount())]
    # KiCad often fractures filled polygons into a self-touching outline. Keep
    # exact coordinates, repair only polygon topology with Shapely, and compare
    # sampled membership against KiCad before using that representation.
    rng = np.random.default_rng(649)
    samples = [[float(x), float(y)] for x, y in rng.uniform(bounds[:2], bounds[2:], (200, 2))]
    membership = [bool(inside(*q)) for q in samples]
    meta = dict(source_sha256=digest, allocation_sha256=hashlib.sha256((ROOT / "Load-allocation-check.json").read_bytes()).hexdigest(),
                ports=ports, allocation=allocation, bounds_mm=bounds, contours=contours,
                native_membership_samples=samples, native_membership=membership)
    (destination / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    print("Extracted saved plane contours and 200 native membership checks", flush=True)


def solve(directory, output):
    import numpy as np
    import shapely
    from shapely.geometry import Polygon
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from ground_sheet import Sheet
    meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    plane = shapely.unary_union([shapely.make_valid(Polygon(c["outline"], c["holes"]))
                                for c in meta["contours"]])
    shapely.prepare(plane)
    probes = np.array(meta["native_membership_samples"])
    assert np.array_equal(shapely.contains_xy(plane, probes[:, 0], probes[:, 1]),
                          meta["native_membership"]), "native/converted plane mismatch"
    bounds = meta["bounds_mm"]
    allocations = meta["allocation"]
    results = []
    for step in [1., .5, .25]:
        xs = np.arange(bounds[0] + step / 2, bounds[2], step)
        ys = np.arange(bounds[1] + step / 2, bounds[3], step)
        xx, yy = np.meshgrid(xs, ys)
        mask = shapely.contains_xy(plane, xx, yy)
        xy = np.c_[xx[mask], yy[mask]]
        ids = np.full(mask.shape, -1); ids[mask] = np.arange(mask.sum())
        edges = []
        for dy, dx in [(0, 1), (1, 0)]:
            a = (slice(None, -dy or None), slice(None, -dx or None))
            b = (slice(dy, None), slice(dx, None))
            valid = mask[a] & mask[b]
            for t in [.25, .5, .75]:
                valid &= shapely.contains_xy(plane, xx[a] + dx * step * t, yy[a] + dy * step * t)
            edges.append(np.c_[ids[a][valid], ids[b][valid]])
        edges = np.concatenate(edges)
        print(f"Extracted {step} mm mesh: {len(xy)} nodes, {len(edges)} edges", flush=True)
        graph = sparse.coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(xy), len(xy)))
        count, label = connected_components(graph, directed=False)
        # Tiny disconnected raster fragments are not the KiCad connectivity
        # verdict. Every current port must map to the same large plane component.
        major = np.bincount(label).argmax(); keep = label == major
        remap = np.full(len(xy), -1); remap[keep] = np.arange(keep.sum())
        discarded = int((~keep).sum())
        edges = remap[edges[np.all(keep[edges], axis=1)]]; xy = xy[keep]
        sheet = Sheet(len(xy), edges, 1.72e-8 / 15.2e-6)
        # 2/3 mm ports are deliberately outside the large connector drill and
        # thermal-clearance scale. Local connection resistance is NOT included.
        for radius in [2., 3.]:
            weights = {}
            for ref, info in meta["ports"].items():
                w = np.zeros(len(xy))
                for site in info["sites"]:
                    dist = np.linalg.norm(xy - site["xy_mm"], axis=1)
                    chosen = np.where(dist <= radius)[0]
                    if not len(chosen):
                        raise ValueError(f"{ref} has no connected plane sample within {radius} mm; nearest {dist.min():.3f} mm; site {site}")
                    w[chosen] += 1 / len(chosen) / len(info["sites"])
                weights[ref] = w
            base = np.zeros(len(xy))
            for rail, regulator in [("logic", "U42"), ("five_volt", "U41")]:
                for load in allocations[rail]["loads"]:
                    base += load["allocation_A"] * (weights[load["ref"]] - weights[regulator])
            cases = [("logic_and_5V_output_loops_only", base, None)]
            # Positive current enters the ground plane. An averaged buck has
            # ground-pin current Iin-Iout; the battery return extracts Iin.
            # These are scenarios, not permitted sustained driver/servo loads.
            for name, vin, efficiency, motor, servo in [
                    ("planning_12V_85percent", 12., .85, .72, .39),
                    ("stress_8V_70percent", 8., .70, 2., 4.)]:
                current = base.copy()
                current += servo * (weights["J90"] - weights["U40"])
                for rail, reg, vout, amps in [
                        ("logic", "U42", 3.318, allocations["logic"]["total_allocated_A"]),
                        ("five", "U41", 5.1, allocations["five_volt"]["total_allocated_A"]),
                        ("servo", "U40", 6.6, servo)]:
                    # Use the unrounded sum to preserve exact current balance.
                    if rail in ["logic", "five"]:
                        key = "logic" if rail == "logic" else "five_volt"
                        amps = sum(r["allocation_A"] for r in allocations[key]["loads"])
                    iin = vout * amps / (vin * efficiency)
                    current += iin * (weights[reg] - weights["J40"])
                current += motor / 2 * (weights["motor_left"] + weights["motor_right"] - 2 * weights["J40"])
                cases.append((name, current, dict(input_V=vin, assumed_efficiency=efficiency,
                                                 motor_total_A=motor, servo_A=servo)))
            rows = []
            for name, current, assumptions in cases:
                voltage, diagnostics = sheet.solve(current)
                values = {ref: float(w @ voltage) for ref, w in weights.items()}
                loads = []
                for rail, reg, feedback in [("logic", "U42", "R431"), ("five_volt", "U41", "R421")]:
                    for row in allocations[rail]["loads"]:
                        delta = values[row["ref"]] - values[feedback]
                        loads.append(dict(ref=row["ref"], plane_return_difference_V=delta,
                                          reference=feedback,
                                          regulator_ground_difference_V=values[row["ref"]] - values[reg],
                                          feed_screen_minus_plane_difference_V=row["static_source_minus_drop_V"] - delta))
                rows.append(dict(name=name, assumptions=assumptions, **diagnostics, loads=loads,
                                 plane_voltage_span_V=float(np.ptp(voltage))))
            results.append(dict(grid_mm=step, port_radius_mm=radius, nodes=len(xy),
                                discarded_raster_nodes=discarded, raster_components=count, cases=rows))
            print(f"Solved {step} mm / {radius} mm ports", flush=True)
    report = dict(source_sha256=meta["source_sha256"], allocation_sha256=meta["allocation_sha256"],
                  fabrication_release=False, copper_thickness_um=15.2, resistivity_ohm_m=1.72e-8,
                  method="Four-neighbour DC resistor sheet sampled from saved In1 ground fill. Distributed current ports near actual ground vias/PTH pads; local pad-to-plane connections are omitted.",
                  limitations=["This is not a guaranteed return-loss bound or a switching-noise/thermal simulation.",
                               "Port projection and finite injection radius omit local tracks, via barrels, thermal spokes, pad spreading and contacts. SMD nearest-stitch projection does not prove a dedicated direct connection.",
                               "Only In1 participates. Other ground layers and parallel vias are omitted. Sub-grid necks/holes can be missed; report mesh and injection-radius sensitivity.",
                               "Load currents and converter efficiencies are assumptions. Driver supply-current proxy does not model PWM recirculation or switching.",
                               "Computed favourable ground offsets must not be used as guaranteed voltage headroom."],
                  native_polygon_membership_checks=200, plane_area_mm2=plane.area,
                  ports=meta["ports"], results=results)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver-python", help="Python executable with NumPy/SciPy/Shapely")
    parser.add_argument("--solve", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, default=ROOT / "Ground-plane-check.json")
    args = parser.parse_args()
    if args.solve:
        solve(args.solve, args.output)
    else:
        if not args.solver_python: parser.error("--solver-python is required")
        with tempfile.TemporaryDirectory(prefix="lab4-ground-") as d:
            extract(Path(d))
            subprocess.run([args.solver_python, str(Path(__file__).resolve()), "--solve", d,
                            "--output", str(args.output)], check=True)
