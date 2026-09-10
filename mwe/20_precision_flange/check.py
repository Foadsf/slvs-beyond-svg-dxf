"""Native geometry, association, and synthetic inspection checks.

SPDX-License-Identifier: CC-BY-SA-4.0
"""
import copy
import hashlib
import json
import math


def inspection(diameter, entry, exit_, spec):
    """Straight axis / circular sections in an ideal planar datum frame only."""
    values = (diameter,*entry,*exit_,*spec.values())
    if not all(math.isfinite(v) for v in values):
        return {"accepted":False,"reason":"nonfinite"}
    error = 2*max(math.hypot(*entry),math.hypot(*exit_))
    available = spec["position_at_mmc"]+diameter-spec["mmc"]
    gap = (diameter-(spec["mmc"]-spec["position_at_mmc"])-error)/2
    size_ok = spec["mmc"]<=diameter<=spec["lmc"]
    return dict(accepted=size_ok and error<=available+1e-10,position=error,
                allowed=available,gap=gap,size_ok=size_ok)


def bound_definition(data,out):
    for model in data["models"]:
        if hashlib.sha256((out.parent/f'{model["name"]}.slvs').read_bytes()).hexdigest()!=model["source_hash"]:
            return False
        for ext,digest in model["hashes"].items():
            if hashlib.sha256((out/f'{model["name"]}.{ext}').read_bytes()).hexdigest()!=digest:
                return False
    return True


def run(ctx):
    s,ex,close=ctx.slvs,ctx.expect,ctx.close
    assoc=json.loads((ctx.here/"associations.json").read_text())
    data=json.loads((ctx.out/"definition.json").read_text())
    ex(bound_definition(data,ctx.out),"definition binds sources and every native, STEP and STL file by SHA-256")
    bad=copy.deepcopy(data);bad["models"][0]["hashes"]["step"]="0"*64
    ex(not bound_definition(bad,ctx.out),"negative control: mismatched STEP hash rejected")
    for name,t in (("flange",12),("flange.t18",18)):
        e=s.entities(ctx.out/f"{name}.slvs")
        c=s.constraints(ctx.out/f"{name}.slvs")
        ex(close(float(c[assoc["thickness_constraint"]]["Constraint.valA"]),t),f"{name}: native driving thickness {t}")
        ex(all(close(a,b) for a,b in zip(s.act_point(e,assoc["boss_top"]),(50,40,t+8))),f"{name}: boss follows flange top")
        for handle,xy in zip(assoc["hole_tops"],[(18,18),(82,18),(82,62),(18,62)]):
            ex(all(close(a,b) for a,b in zip(s.act_point(e,handle),(*xy,t))),f"{name}: bore top {xy} follows thickness")
        for handle in assoc["mounting_circles"]:
            ex(close(float(e[e[handle]["Entity.distance.v"]]["Entity.actDistance"]),4.2),f"{name}: equal mounting radii solve to 4.2")
        ex(close(float(e[e[assoc["pilot_circle"]]["Entity.distance.v"]]["Entity.actDistance"]),12),f"{name}: pilot radius solves to 12")
        pmi=json.loads((ctx.out/f"{name}.pmi.json").read_text())
        defined=next(m for m in data["models"] if m["name"]==name)
        ex(defined["pmi"]==pmi,f"{name}: definition PMI equals the native extraction")
        datums={d["datum"]:d["anchor_xyz"] for d in pmi["datums"]}
        ex(set(datums)=={"A","B","C"} and close(datums["A"][2],0)
           and close(datums["B"][1],0) and close(datums["C"][0],0),f"{name}: datum anchors lie on their stated planes")
        note=next(n for n in pmi["notes"] if n["handle"]==assoc["position_note"])
        ex(note["anchor_xyz"]==[82,18,t],f"{name}: native position FCF remains attached")
        box=ctx.stl_bbox(ctx.out/f"{name}.stl")
        ex(all(close(a,b) for pair,want in zip(box,[(0,100),(0,80),(0,t+8)]) for a,b in zip(pair,want)),f"{name}: STL bounds match all three sizes",box)
        ex("CONFIG_CONTROL_DESIGN" in (ctx.out/f"{name}.step").read_text(),f"{name}: STEP schema explicitly AP203")
        ex(close(s.params(ctx.here/f"{name}.slvs")["80030002"],4) and close(s.params(ctx.out/f"{name}.slvs")["80030002"],t/2),f"{name}: extrusion solved from an intentionally wrong initial guess")
    a=(ctx.here/"flange.slvs").read_bytes().splitlines();b=(ctx.here/"flange.t18.slvs").read_bytes().splitlines()
    changed=[(x,y) for x,y in zip(a,b) if x!=y]
    ex(len(a)==len(b) and changed==[(b"Constraint.valA=12",b"Constraint.valA=18")],"source variants differ by exactly one driving value")
    spec=data["models"][0]["inspection"]
    cases=[("bonus pass",8.5,(.12,.06),(.12,.06),True),
           ("MMC fail",8.4,(.12,.06),(.12,.06),False),
           ("tilted exit fail",8.5,(.12,.06),(.18,.06),False),
           ("undersize centered fail",8.39,(0,0),(0,0),False),
           ("oversize centered fail",8.61,(0,0),(0,0),False),
           ("boundary pass",8.4,(.1,0),(.1,0),True),
           ("nonfinite fail",float('nan'),(0,0),(0,0),False)]
    reports=[]
    for name,d,entry,exit_,expected in cases:
        m=inspection(d,entry,exit_,spec)
        ex(m["accepted"]==expected,f"synthetic inspection: {name}",m)
        reports.append(dict(case=name,expected=expected,measurement=m))
    # Independently evaluate swept pin containment at 101 axial stations.
    for d in (8.4,8.5,8.6):
        for x in (0,.05,.12,.2):
            for tilt in (0,.03,.12):
                m=inspection(d,(x,.06),(x+tilt,.06),spec)
                clearance=min(d/2-spec["virtual_condition"]/2-math.hypot(x+tilt*i/100,.06) for i in range(101))
                ex(m["accepted"]==(clearance>=-1e-10),f"axis-zone / swept-pin duality d={d}, x={x}, tilt={tilt}")
    (ctx.out/"inspection-evidence.json").write_text(json.dumps(reports,indent=2)+"\n")
