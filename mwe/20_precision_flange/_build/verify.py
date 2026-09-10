"""Reopen native STEP exports in OpenCascade; verify volume and all bore walls.

Run in a Python environment containing cadquery. No CAD is authored here.
SPDX-License-Identifier: CC-BY-SA-4.0
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import cadquery as cq

HERE=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stl-inspector",required=True)
    args=ap.parse_args()
    spec=importlib.util.spec_from_file_location("stl_inspect",args.stl_inspector)
    stl=importlib.util.module_from_spec(spec);spec.loader.exec_module(stl)
    evidence=[]
    for name,t in (("flange",12),("flange.t18",18)):
        path=HERE/"out"/f"{name}.step"
        shape=cq.importers.importStep(str(path)).val()
        assert shape.isValid() and len(shape.Solids())==1,"not one valid solid"
        exact=(100*80-4*10*10/2-math.pi*(12**2+4*4.2**2))*t+math.pi*(20**2-12**2)*8
        measured=shape.Volume()
        assert abs(measured-exact)<.05,(measured,exact)
        box=shape.BoundingBox()
        assert max(abs(a-b) for a,b in zip((box.xlen,box.ylen,box.zlen),(100,80,t+8)))<1e-4
        solid=shape.Solids()[0]
        probes=0
        for x,y,r,height in [(50,40,12,t+8),*( (x,y,4.2,t) for x,y in [(18,18),(82,18),(82,62),(18,62)])]:
            for z in (.25,height/2,height-.25):
                for angle in range(0,360,45):
                    ux,uy=math.cos(math.radians(angle)),math.sin(math.radians(angle))
                    assert not solid.isInside((x+(r-.01)*ux,y+(r-.01)*uy,z),1e-6)
                    assert solid.isInside((x+(r+.01)*ux,y+(r+.01)*uy,z),1e-6)
                    probes+=2
        assert solid.isInside((50,10,t/2),1e-6),"solid web control must reject a bore claim"
        assert not solid.isInside((1,1,t/2),1e-6),"clipped corner must be absent"
        assert solid.isInside((50+19.99,40,t+4),1e-6) and not solid.isInside((50+20.01,40,t+4),1e-6)
        tris,_=stl.load_stl(HERE/"out"/f"{name}.stl")
        topo=stl.topology(tris)
        assert topo["watertight"] and not topo["degenerate_triangles"]
        assert topo["vertices"]-topo["edges"]+topo["triangles"]==-8,"five through bores -> genus 5"
        assert not stl.topology(tris[1:])["watertight"],"missing facet must fail"
        meshvol=stl.mesh_volume(tris)
        assert abs(meshvol-exact)/exact<.003
        evidence.append(dict(model=name,step_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             step_valid=True,solids=1,expected_volume_mm3=exact,step_volume_mm3=measured,
                             bore_boundary_probes=probes,stl_watertight=True,stl_euler=-8,stl_volume_mm3=meshvol,
                             controls=["solid web is not a hole","missing triangle is not watertight"]))
    (HERE/"out/solid-evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(evidence,indent=2))


if __name__=="__main__":
    main()
