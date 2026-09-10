"""Author native SolveSpace requests; bootstrap only to discover extrusion handles.

SPDX-License-Identifier: CC-BY-SA-4.0
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import slvs
from build import find_cli, run


def hx(n):
    return f"{n:08x}"


def record(kind, fields):
    return "".join(f"{kind}.{k}={v}\n" for k, v in fields.items()) + f"Add{kind}\n\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cli", required=True)
    cli = find_cli(ap.parse_args().cli)
    rows = []
    def add(kind, **kw):
        rows.append(record(kind, kw))
    def group(g, typ, name, **kw):
        add("Group", **{"h.v": hx(g), "type": typ, "order": g-1,
                       "name": name, "scale": 1, "visible": 1, **kw})
    def req(r, typ, g, points, radius=None):
        add("Request", **{"h.v": hx(r), "type": typ, "group.v": hx(g),
                         "workplane.v": hx(0x80000000 | g << 16)})
        for i, p in enumerate(points):
            for axis, value in enumerate(p):
                add("Param", **{"h.v.": hx((r << 16)+16+3*i+axis), "val": value})
        if radius is not None:
            add("Param", **{"h.v.": hx((r << 16)+64), "val": radius})
    n = 0
    def c(typ, g=2, **kw):
        nonlocal n
        n += 1
        add("Constraint", **{"h.v": hx(n), "type": typ, "group.v": hx(g),
                             **({"workplane.v": hx(0x80000000 | g << 16)} if g in (2,4) else {}), **kw})
        return hx(n)
    def extrusion(g, sketch, name):
        group(g, 5100, name, **{"opA.v": hx(sketch), "subtype":7000,
              "predef.entityB.v":hx(0x80000000 | sketch << 16), "color":"00b8ad7f"})
        for axis, value in enumerate((0, 0, 4)):
            add("Param", **{"h.v.":hx(0x80000000 | g << 16 | axis), "val":value})
    group(1, 5000, "#references")
    for r in (1,2,3):
        add("Request", **{"h.v":hx(r), "type":100, "group.v":hx(1)})
    group(2, 5001, "flange-outline-and-bores", **{"activeWorkplane.v":"80020000",
          "subtype":6000, "predef.q.w":1, "predef.origin.v":"00010001"})
    corners = [(10,0),(90,0),(100,10),(100,70),(90,80),(10,80),(0,70),(0,10)]
    for i, point in enumerate(corners):
        r = 10+i
        req(r,200,2,[point,corners[(i+1)%8]])
        # Fixed nominal contour; diameter/equality and both extrusions remain driving constraints.
        c(200, **{"ptA.v":hx(r<<16 | 1)})
        c(20, **{"ptA.v":hx(r<<16 | 2),"ptB.v":hx((10+(i+1)%8)<<16 | 1)})
    holes = [(50,40),(18,18),(82,18),(82,62),(18,62)]
    for i, point in enumerate(holes):
        r = 30+i
        req(r,400,2,[point],radius=10 if i==0 else 3.7)
        c(200, **{"ptA.v":hx(r<<16 | 1)})
        if i<2:
            c(90, **{"entityA.v":hx(r<<16),"valA":24 if i==0 else 8.4})
        else:
            c(130, **{"entityA.v":hx(r<<16),"entityB.v":hx(31<<16)})
    extrusion(3,2,"mounting-flange")
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    boot = out / "bootstrap.slvs"
    def bootstrap():
        boot.write_bytes(slvs.MAGIC_RAW+b"\n\n"+"".join(rows).encode("ascii"))
        run(cli,"regenerate",str(boot))
    def mapped(g, entity):
        rec = next(r for r in slvs.parse(boot) if r.get("Group.h.v")==hx(g))
        idx = next(int(p[0]) for row in rec["Group.remap"]
                   if (p:=row.split())[1:] == [entity,"1001"])
        return hx(0x80000000 | g << 16 | idx)
    bootstrap()
    top_corner = mapped(3,hx(10<<16 | 1))
    thickness = c(30,3, **{"ptA.v":hx(10<<16 | 1),"ptB.v":top_corner,"valA":12,
                         "disp.offset.x":-12,"disp.offset.y":-12})
    top_bore = mapped(3,hx(30<<16 | 1))
    hole_tops = [mapped(3,hx(r<<16 | 1)) for r in range(31,35)]
    group(4,5001,"boss-profile-on-flange", **{"activeWorkplane.v":"80040000",
          "subtype":6000,"predef.q.w":1,"predef.origin.v":top_bore})
    for r, radius in [(40,18),(41,10)]:
        req(r,400,4,[(0,0)],radius)
        c(20,4, **{"ptA.v":hx(r<<16 | 1),"ptB.v":"80040002"})
    c(90,4, **{"entityA.v":hx(40<<16),"valA":40})
    c(130,4, **{"entityA.v":hx(41<<16),"entityB.v":hx(30<<16)})
    extrusion(5,4,"integral-pilot-boss")
    bootstrap()
    boss_top = mapped(5,hx(40<<16 | 1))
    c(30,5, **{"ptA.v":hx(40<<16 | 1),"ptB.v":boss_top,"valA":8,
              "disp.offset.x":25,"disp.offset.y":15})
    def note(text, anchor=None, offset=(0,0,0)):
        return c(1000,5, **{"comment":text, **({"ptA.v":anchor} if anchor else {}),
                 **{f"disp.offset.{axis}":v for axis,v in zip("xyz",offset)}})
    datum_notes = [note("DATUM A : mounting face Z=0; [FLAT|0.05]",hx(10<<16 | 1),(-5,-25,0)),
                   note("DATUM B : side Y=0; [PERP|0.05|A]",hx(10<<16 | 2),(15,-12,0)),
                   note("DATUM C : side X=0; [PERP|0.05|A|B]",hx(17<<16 | 1),(-35,0,0))]
    position_note = note("4X DIA 8.40-8.60 THRU; [POS|DIA 0.20 (M)|A|B|C]",hole_tops[1],(26,-10,20))
    note("PILOT DIA 24.00-24.02 THRU; [POS|DIA 0.05|A|B|C]",boss_top,(0,33,8))
    note("BOSS TOP [PARALLEL|0.05|A]; DIA 40 +/-0.10",boss_top,(-48,12,7))
    note("BASIC XY: (18,18) (82,18) (82,62) (18,62); PILOT (50,40)",None,(50,108,20))
    note("PF-020 / REV A / mm / EDUCATIONAL DEFINITION",None,(50,123,20))
    note("MATERIAL 6061-T6 ALUMINIUM; UNCOATED; DEBURR 0.2 MAX",None,(50,115,20))
    note("MACHINED Ra 3.2 um; A AND PILOT Ra 1.6 um; LINEAR +/-0.10",None,(50,-37,0))
    raw = (slvs.MAGIC_RAW+b"\n\n"+"".join(rows).encode("ascii")).rstrip(b"\n")+b"\n"
    (HERE/"flange.slvs").write_bytes(raw)
    tag = f"Constraint.h.v={thickness}\n".encode()
    head,tail = raw.split(tag)
    variant = head+tag+tail.replace(b"Constraint.valA=12\n",b"Constraint.valA=18\n",1)
    (HERE/"flange.t18.slvs").write_bytes(variant)
    associations = {"thickness_constraint":thickness,"top_bore":top_bore,"boss_top":boss_top,
                    "hole_tops":hole_tops,"position_note":position_note,"datum_notes":datum_notes,
                    "pilot_circle":hx(30<<16),"mounting_circles":[hx(r<<16) for r in range(31,35)]}
    (HERE/"associations.json").write_text(json.dumps(associations,indent=2)+"\n")
    print("Authored two native sources; one driving thickness line differs.")


if __name__ == "__main__":
    main()
