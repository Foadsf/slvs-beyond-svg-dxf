"""Dress the native mechanism with seven constrained capsule links and bores.

All hole centres project the native skeleton joints. Altering the skeleton's
one drive dimension therefore moves the solid profiles during regeneration.
Layers are an exploded educational arrangement, not a finished pivot stack.
SPDX-License-Identifier: CC-BY-SA-4.0
"""
import argparse
import math
from sweep import HERE, checks, find_cli, replace_value, run_cli, slvs


def hx(value):
    return f"{value:08x}"


def record(kind, fields):
    return "\n".join(f"{kind}.{key}={value}" for key, value in fields.items()) + f"\nAdd{kind}\n\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cli")
    args = ap.parse_args()
    cli = find_cli(args.cli)
    out = HERE / "out"
    p = checks.points(slvs, out / "linkage.slvs")
    source = (HERE / "linkage.slvs").read_bytes()
    # The sketch remains native; only hide its construction lines in the solid view.
    source = source.replace(b"Request.construction=1\n", b"")
    source = source.replace(b"Request.type=200\n", b"Request.type=200\nRequest.construction=1\n")
    source = source.replace(b"Group.visible=1\n", b"Group.visible=0\n")
    rows = []
    def add(kind, **fields):
        rows.append(record(kind, fields))
    add("Group", **{"h.v": hx(3), "type": 5000, "order": 2, "name": "layer-origins", "scale": 1})
    for i in range(7):
        r = 500 + i
        add("Request", **{"h.v": hx(r), "type": 101, "group.v": hx(3)})
        for axis, v in enumerate((0, 0, i * 3)):
            add("Param", **{"h.v.": hx((r << 16) + 16 + axis), "val": v})
        add("Constraint", **{"h.v": hx(100 + i), "type": 200, "group.v": hx(3), "ptA.v": hx(r << 16)})
    for i, (a, b) in enumerate(checks.BAR_PAIRS):
        g, r, n = 4 + i * 2, 100 + i * 10, 200 + i * 30
        wp = hx(0x80000000 | (g << 16))
        add("Group", **{"h.v": hx(g), "type": 5001, "order": g-1, "name": f"profile-{a}{b}",
                        "activeWorkplane.v": wp, "subtype": 6000, "predef.q.w": 1,
                        "predef.origin.v": hx((500 + i) << 16), "scale": 1})
        add("Group", **{"h.v": hx(g+1), "type": 5100, "order": g, "name": f"link-{a}{b}",
                        "opA.v": hx(g), "subtype": 7000, "predef.entityB.v": wp,
                        "meshCombine": 2, "color": "007ab6de" if i < 2 else "00ccad6c" if i < 6 else "0088c59c",
                        "visible": 1, "scale": 1})
        for axis, v in enumerate((0, 0, 1.4)):
            add("Param", **{"h.v.": hx(0x80000000 | ((g+1) << 16) | axis), "val": v})
        ax, ay = p[a]; bx, by = p[b]
        length = math.hypot(bx-ax, by-ay)
        nx, ny = -(by-ay)/length*5, (bx-ax)/length*5
        aup, alo = (ax+nx, ay+ny), (ax-nx, ay-ny)
        bup, blo = (bx+nx, by+ny), (bx-nx, by-ny)
        geometry = [(500, [p[a], aup, alo]), (500, [p[b], blo, bup]),
                    (200, [aup, bup]), (200, [alo, blo]), (400, [p[a]]), (400, [p[b]])]
        for j, (typ, seeds) in enumerate(geometry):
            add("Request", **{"h.v": hx(r+j), "type": typ, "group.v": hx(g), "workplane.v": wp})
            for k, pt in enumerate(seeds):
                for axis, v in enumerate(pt):
                    add("Param", **{"h.v.": hx(((r+j) << 16) + 16 + 3*k + axis), "val": f"{v:.14f}"})
            if typ == 400:
                add("Param", **{"h.v.": hx(((r+j) << 16) + 64), "val": 2.5})
        def c(typ, **fields):
            nonlocal n
            n += 1
            add("Constraint", **{"h.v": hx(n), "type": typ, "group.v": hx(g), "workplane.v": wp, **fields})
        def ent(j, k=0):
            return hx(((r+j) << 16) + k)
        c(20, **{"ptA.v": ent(0, 1), "ptB.v": checks.JOINTS[a]})
        c(20, **{"ptA.v": ent(1, 1), "ptB.v": checks.JOINTS[b]})
        c(90, **{"entityA.v": ent(0), "valA": 10})
        c(130, **{"entityA.v": ent(0), "entityB.v": ent(1)})
        for j, k, l, m in [(2, 1, 0, 2), (2, 2, 1, 3), (3, 1, 0, 3), (3, 2, 1, 2)]:
            c(20, **{"ptA.v": ent(j, k), "ptB.v": ent(l, m)})
        for arc, line, other in [(0, 2, 0), (0, 3, 1), (1, 2, 1), (1, 3, 0)]:
            c(123, **{"entityA.v": ent(arc), "entityB.v": ent(line), "other": other})
        for j, center in [(4, 0), (5, 1)]:
            c(20, **{"ptA.v": ent(j, 1), "ptB.v": ent(center, 1)})
            c(90, **{"entityA.v": ent(j), "valA": 5})
    raw = source + "".join(rows).encode("ascii")
    draft = out / "assembly.bootstrap.slvs"
    draft.write_bytes(raw)
    run_cli(cli, "regenerate", draft)
    # Discover SolveSpace's actual generated handles; never guess a remap index.
    records = slvs.parse(draft)
    for i in range(7):
        g, r = 5 + i*2, 100 + i*10
        group = next(x for x in records if x.get("Group.h.v") == hx(g))
        center = hx((r << 16) + 1)
        mappings = [x.split() for x in group["Group.remap"]]
        index = next(int(x[0], 16) for x in mappings if x[1] == center and x[2] == "1001")
        top = hx(0x80000000 | (g << 16) | index)
        raw += record("Constraint", {"h.v": hx(600+i), "type": 30, "group.v": hx(g),
                                     "ptA.v": center, "ptB.v": top, "valA": 2}).encode()
    logs = []
    for name, height in [("assembly", 10), ("assembly.height25", 25)]:
        path = out / f"{name}.slvs"
        if height == 10:
            path.write_bytes(raw)
            logs.append(run_cli(cli, "regenerate", path))
        else:
            seed = (out / "assembly.slvs").read_bytes()
            for step in range(11, height+1):
                path.write_bytes(replace_value(seed, "00000015", -step))
                logs.append(run_cli(cli, "regenerate", path))
                seed = path.read_bytes()
        m = checks.measurements(checks.points(slvs, path), height)
        if not checks.valid(m):
            raise AssertionError(m)
        params = slvs.params(path)
        entities = slvs.entities(path)
        for i, (a, b) in enumerate(checks.BAR_PAIRS):
            g, r = 5+i*2, 100+i*10
            assert abs(params[hx(0x80000000 | (g << 16) | 2)]-1) < 1e-7
            for j, joint in [(4,a),(5,b)]:
                center = slvs.act_point(entities, hx(((r+j) << 16)+1))
                target = slvs.act_point(entities, checks.JOINTS[joint])
                assert math.dist(center[:2], target[:2]) < 1e-6 and abs(center[2]-3*i) < 1e-6
        for command, pattern, extra in [
                ("export-surfaces", "%.step", []),
                ("export-mesh", "%.stl", ["--chord-tol", "0.03"]),
                ("thumbnail", "%.iso.png", ["--view", "isometric", "--size", "1200x900"]),
                ("export-view", "%.iso.svg", ["--view", "isometric", "--bg-color", "off"])]:
            logs.append(run_cli(cli, command, "--output", pattern, *extra, path))
            assert (out / (name + pattern[1:])).stat().st_size > 0
        print(f"{name}: native skeleton, 14 projected bore centres, 7 thicknesses verified; STEP/STL exported", flush=True)
    (out / "solid-build.log").write_text("".join(logs), encoding="utf-8")


if __name__ == "__main__":
    main()
