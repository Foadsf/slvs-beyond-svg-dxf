"""Independently reopen SolveSpace STEP/STL exports with OpenCascade and stl_inspect.

Requires cadquery-ocp and --stl-inspector PATH to the existing stl_inspect.py tool.
SPDX-License-Identifier: CC-BY-SA-4.0
"""
import json
import math
import argparse
import importlib.util
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_IN
from OCP.TopoDS import TopoDS
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from sweep import HERE, checks, slvs


def volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props, 1e-9)
    return props.Mass()


def zlimits(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box)
    xyz = box.Get()
    return xyz[2], xyz[5]


def inside(shape, point):
    classifier = BRepClass3d_SolidClassifier(shape)
    classifier.Perform(gp_Pnt(*point), 1e-6)
    return classifier.State() == TopAbs_IN


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stl-inspector", required=True)
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("stl_inspect", args.stl_inspector)
    stl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stl)
    reports = []
    for name, height in [("assembly", 10), ("assembly.height25", 25)]:
        native = HERE / "out" / (name + ".slvs")
        p = checks.points(slvs, native)
        assert checks.valid(checks.measurements(p, height)), "native mechanism violates references"
        reader = STEPControl_Reader()
        assert reader.ReadFile(str(HERE / "out" / (name + ".step"))) == IFSelect_RetDone
        assert reader.TransferRoots() > 0
        shape = reader.OneShape()
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        bodies = []
        while explorer.More():
            bodies.append(TopoDS.Solid_s(explorer.Current()))
            explorer.Next()
        bodies.sort(key=lambda s: zlimits(s)[0])
        assert BRepCheck_Analyzer(shape).IsValid() and len(bodies) == 7, "expected seven valid STEP solids"
        sizes = [100, 100, 60, 60, 60, 60, 35]
        bore_checks = 0
        for i, (body, length, (a, b)) in enumerate(zip(bodies, sizes, checks.BAR_PAIRS)):
            # Capsule area minus two radius-2.5 bores, times 2 mm thickness.
            exact = (10*length + math.pi*5**2 - 2*math.pi*2.5**2)*2
            assert abs(volume(body)-exact) < 0.01, (i, volume(body), exact)
            zmin,zmax = zlimits(body)
            assert abs(zmin-3*i) < 1e-5 and abs(zmax-(3*i+2)) < 1e-5
            dx, dy = p[b][0]-p[a][0], p[b][1]-p[a][1]
            normal = (-dy/length, dx/length)
            for joint in (a,b):
                x, y = p[joint]
                for side in (-1, 1):
                    inner = (x+side*normal[0]*2.49, y+side*normal[1]*2.49, 3*i+1)
                    outer = (x+side*normal[0]*2.51, y+side*normal[1]*2.51, 3*i+1)
                    assert not inside(body, inner) and inside(body, outer), (i,joint,"bore radius")
                    bore_checks += 1
        triangles, _ = stl.load_stl(HERE / "out" / (name + ".stl"))
        layers = [[] for _ in range(7)]
        for triangle in triangles:
            indices = [round(v[2] // 3) for v in triangle]
            assert len(set(indices)) == 1 and 0 <= indices[0] < 7
            layers[indices[0]].append(triangle)
        topo = [stl.topology(layer) for layer in layers]
        assert all(t["watertight"] and t["triangles"] and not t["degenerate_triangles"] for t in topo)
        euler = [t["vertices"]-t["edges"]+t["triangles"] for t in topo]
        assert all(v == -2 for v in euler), "each link must have two through bores"
        assert not stl.topology(layers[0][1:])["watertight"], "missing-facet control must fail"
        mesh_volume = stl.mesh_volume(triangles)
        exact_total = (10*sum(sizes) + 7*math.pi*(25-12.5))*2
        # Meshed arcs have 0.03 mm chord tolerance; volume is secondary to topology.
        assert abs(mesh_volume-exact_total) / exact_total < 0.002
        reports.append(dict(file=name, step_valid=True, step_solids=len(bodies),
                            expected_volume_mm3=exact_total, step_volume_mm3=volume(shape),
                            bore_boundary_checks=bore_checks, stl_layers=len(layers),
                            stl_watertight=all(t["watertight"] for t in topo),
                            stl_euler_per_layer=euler, stl_volume_mm3=mesh_volume))
    # Negative control exercises the same bore predicate against solid material.
    body = bodies[0]
    a,b = checks.BAR_PAIRS[0]
    mid = ((p[a][0]+p[b][0])/2, (p[a][1]+p[b][1])/2, 1)
    assert inside(body, mid), "control must distinguish a solid web from a bore"
    result = dict(results=reports, negative_controls=["solid web rejected as a bore", "missing facet rejected as watertight"])
    (HERE / "out" / "solid-evidence.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
