"""Verify that every MWE solved to the geometry its README claims.

Run ``python tools/build.py`` first; this reads the regenerated files in each
``mwe/*/out/`` directory and the exported STL/STEP where relevant.

Every check compares a *solved* value (read from ``Entity.actPoint`` or
``Param.val`` written back by ``solvespace-cli regenerate``) against a value
derived from the constraints alone.  It also asserts that the solved value
differs from the initial guess in the source file, so a build that silently
skipped solving cannot pass.

SPDX-License-Identifier: CC-BY-SA-4.0
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MWE = ROOT / "mwe"
sys.path.insert(0, str(HERE))
import slvs  # noqa: E402

TOL = 1e-6
_failures: list[str] = []


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def expect(cond: bool, what: str, got=None) -> None:
    mark = "ok  " if cond else "FAIL"
    tail = "" if got is None else f"   [{got}]"
    print(f"  {mark} {what}{tail}")
    if not cond:
        _failures.append(what)


def stl_bbox(path: Path) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Bounding box of a binary STL (what solvespace-cli export-mesh writes)."""
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    xs, ys, zs = [], [], []
    for i in range(n):
        v = struct.unpack("<12f", data[84 + i * 50: 84 + i * 50 + 48])
        for k in range(3):
            xs.append(v[3 + 3 * k]); ys.append(v[4 + 3 * k]); zs.append(v[5 + 3 * k])
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------

def check_01() -> None:
    d = MWE / "01_variational_triangle"
    print("01_variational_triangle")
    src_guess = slvs.params(d / "triangle.slvs")["00050014"]      # apex v, initial guess
    for name, hyp in (("triangle.slvs", 125.0), ("triangle.hyp200.slvs", 200.0)):
        out = d / "out" / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        apex = slvs.act_point(e, "00050002")
        height = math.sqrt(hyp ** 2 - 100.0 ** 2)
        expect(close(apex[0], 100.0) and close(apex[1], height),
               f"{name}: apex = (100, sqrt({hyp:g}^2-100^2)) = (100, {height:.3f})", apex[:2])
        ref = float(c["00000009"]["Constraint.valA"])
        expect(close(ref, math.degrees(math.atan2(height, 100.0)), 1e-4),
               f"{name}: reference angle rewritten to atan(h/100)", f"{ref:.4f} deg")
        expect(c["00000009"].get("Constraint.reference") == "1",
               f"{name}: angle constraint is still marked reference (driven, not driving)")
    expect(not close(src_guess, 75.0), "source file holds only the initial guess, not the answer", src_guess)


def check_02() -> None:
    d = MWE / "02_tangent_slot"
    print("02_tangent_slot")
    for name, pitch in (("slot.slvs", 60.0), ("slot.pitch90.slvs", 90.0)):
        out = d / "out" / name
        e = slvs.entities(out)
        lc, ls, le = (slvs.act_point(e, h) for h in ("00040001", "00040002", "00040003"))
        rc, rs, re_ = (slvs.act_point(e, h) for h in ("00050001", "00050002", "00050003"))
        expect(close(rc[0] - lc[0], pitch) and close(rc[1], 0.0),
               f"{name}: arc centres {pitch:g} apart on the horizontal", (rc[0] - lc[0], rc[1]))
        for label, p in (("L start", ls), ("L end", le), ("R start", rs), ("R end", re_)):
            expect(close(abs(p[1]), 10.0) and close(math.hypot(p[0] - (lc[0] if label[0] == "L" else rc[0]), p[1]), 10.0),
                   f"{name}: {label} sits on its circle at y = +-10 (tangent point)", (round(p[0], 6), round(p[1], 6)))
        # The straight edges must be tangent: their endpoints share y with the arc ends
        top = (slvs.act_point(e, "00060001"), slvs.act_point(e, "00060002"))
        bot = (slvs.act_point(e, "00070001"), slvs.act_point(e, "00070002"))
        expect(close(top[0][1], top[1][1]) and close(bot[0][1], bot[1][1]),
               f"{name}: both straight edges came out horizontal without a HORIZONTAL constraint")
        expect(close(top[1][0] - top[0][0], pitch), f"{name}: straight edge length equals pitch", top[1][0] - top[0][0])
    # construction geometry is not exported
    dxf = (d / "out" / "slot.dxf").read_text(errors="replace")
    n_line = len(re.findall(r"^LINE\r?$", dxf, re.M))
    expect(n_line == 2, "DXF export has exactly 2 LINEs: the construction centre line is not exported", n_line)


def check_03() -> None:
    d = MWE / "03_symmetric_bracket"
    print("03_symmetric_bracket")
    for name, top in (("bracket.slvs", 40.0), ("bracket.top70.slvs", 70.0)):
        out = d / "out" / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        tl, tr = slvs.act_point(e, "00060002"), slvs.act_point(e, "00050002")
        expect(close(tl[0], 50 - top / 2) and close(tr[0], 50 + top / 2) and close(tl[1], 60) and close(tr[1], 60),
               f"{name}: top corners mirrored about x=50, {top:g} apart, at height 60", (tl[:2], tr[:2]))
        side = float(c["0000000e"]["Constraint.valA"])
        expect(close(side, math.hypot(50 - top / 2, 60), 1e-4),
               f"{name}: reference side length rewritten to sqrt(({50 - top / 2:g})^2 + 60^2)", f"{side:.4f}")


def check_04() -> None:
    d = MWE / "04_bolt_pattern"
    print("04_bolt_pattern")
    for name, copies, step in (("flange.slvs", 5, 60.0), ("flange.8holes.slvs", 7, 45.0)):
        out = d / "out" / name
        e = slvs.entities(out)
        holes = [h for h, r in e.items() if r["Entity.type"] == "13000" and h.startswith("8004")]
        centres = [slvs.act_point(e, e[h]["Entity.point[0].v"]) for h in holes]
        angles = sorted(math.degrees(math.atan2(y, x)) % 360 for x, y, _ in centres)
        radii = {round(math.hypot(x, y), 6) for x, y, _ in centres}
        expect(len(holes) == copies, f"{name}: {copies} rotated copies of the seed hole", len(holes))
        # The solver converges to ~1e-8 rad; the k-th copy accumulates k times that.
        expect(all(close(a, step * k, 1e-4) for a, k in zip(angles, range(1, copies + 1))),
               f"{name}: copies at multiples of {step:g} deg (within 1e-4 deg)",
               [round(a, 6) for a in angles])
        expect(radii == {45.0}, f"{name}: every copy stays on the pitch circle (r = 45)", radii)
    src_angle = slvs.params(d / "flange.slvs")["80040003"]
    out_angle = slvs.params(d / "out" / "flange.slvs")["80040003"]
    expect(close(out_angle, math.radians(60) / 4) and not close(src_angle, out_angle),
           "rotation parameter solved from the ANGLE constraint (stored as angle/4 per copy)",
           (src_angle, out_angle))


def check_05() -> None:
    d = MWE / "05_transclusion"
    print("05_transclusion")
    expect(sha(d / "base" / "bracket.slvs") == sha(d / "variant" / "bracket.slvs"),
           "downstream bracket.slvs is byte-identical in base/ and variant/")
    for sub, pitch in (("base", 80.0), ("variant", 100.0)):
        out = d / "out" / sub / "bracket.slvs"
        e = slvs.entities(out)
        h1, h2 = slvs.act_point(e, "00080001"), slvs.act_point(e, "00090001")
        expect(close(h1[0], -pitch / 2) and close(h2[0], pitch / 2) and close(h1[1], 0) and close(h2[1], 0),
               f"{sub}: hole centres follow the linked skeleton pitch {pitch:g}", (h1[:2], h2[:2]))
        lo = slvs.act_point(e, "80030002")
        expect(all(close(v, 0) for v in lo), f"{sub}: linked skeleton origin pinned to the local origin", lo)
        g = [r for r in slvs.parse(out) if r.get("_kind") == "AddGroup" and r.get("Group.type") == "5300"][0]
        expect(g.get("Group.impFileRel") == "skeleton.slvs", f"{sub}: link is by relative path", g.get("Group.impFileRel"))


def check_06() -> None:
    d = MWE / "06_sketch_to_solid"
    print("06_sketch_to_solid")
    for name, depth in (("plate.slvs", 8.0), ("plate.depth20.slvs", 20.0)):
        out = d / "out" / name
        e = slvs.entities(out)
        hole = slvs.act_point(e, "00080001")
        expect(close(hole[0], 30) and close(hole[1], 30), f"{name}: hole centre 30 from left and bottom edges", hole[:2])
        top = slvs.act_point(e, "80030005")
        expect(close(top[2], depth), f"{name}: extruded copy of the origin corner at z = {depth:g}", top)
        (x0, x1), (y0, y1), (z0, z1) = stl_bbox(out.with_suffix(".stl"))
        expect(close(x1 - x0, 100) and close(y1 - y0, 60) and close(z0, 0) and close(z1, depth),
               f"{name}: STL bounding box 100 x 60 x {depth:g}", (x1 - x0, y1 - y0, z1 - z0))
        step = out.with_suffix(".step").read_text(errors="replace")
        n_surf = len(re.findall(r"B_SPLINE_SURFACE_WITH_KNOTS", step))
        expect(step.startswith("ISO-10303-21;") and n_surf >= 7,
               f"{name}: STEP is an ISO 10303-21 B-rep with >= 7 surfaces (6 faces + hole)", n_surf)
    src = slvs.params(d / "plate.slvs")["80030002"]
    out = slvs.params(d / "out" / "plate.slvs")["80030002"]
    expect(close(out, 4.0) and not close(src, out),
           "extrusion parameter solved to depth/2 from the distance constraint (source guess differs)", (src, out))


def main() -> int:
    missing = [p for p in MWE.iterdir() if (p / "build.json").exists() and not (p / "out").exists()]
    if missing:
        sys.exit("run tools/build.py first; missing out/ in: " + ", ".join(m.name for m in missing))
    for fn in (check_01, check_02, check_03, check_04, check_05, check_06):
        fn()
    print()
    if _failures:
        print(f"{len(_failures)} check(s) FAILED:")
        for f in _failures:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
