"""Checks for 12_gdt_form_flatness.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import itertools
import math

POINTS = ["00050000", "00060000", "00070000", "00080000", "00090000", "000a0000"]


def min_zone(pts):
    """Minimum-width band enclosing 2D points: two points on one boundary, one on the other."""
    best = None
    for a, b in itertools.combinations(range(len(pts)), 2):
        (x1, y1), (x2, y2) = pts[a], pts[b]
        L = math.hypot(x2 - x1, y2 - y1)
        ds = [((x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)) / L for x, y in pts]
        w = max(ds) - min(ds)
        if best is None or w < best[0]:
            best = (w, a, b)
    return best


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, peak in (("surface.slvs", 60.6), ("surface.bump.slvs", 61.2)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        pts = [slvs.act_point(e, h)[:2] for h in POINTS]
        expect(close(pts[2][1], peak), f"{name}: measured points pinned by WHERE_DRAGGED (peak y = {peak:g})", pts[2])
        flat = abs(float(c["0000001c"]["Constraint.valA"]))
        par = abs(float(c["00000025"]["Constraint.valA"]))
        w, a, b = min_zone(pts)
        expect(close(flat, w, 1e-6), f"{name}: flatness reference == brute-force minimum zone ({w:.4f}), contacts {a},{b} + 2",
               round(flat, 6))
        ys = [p[1] for p in pts]
        expect(close(par, max(ys) - min(ys), 1e-6), f"{name}: parallelism reference == max y - min y", round(par, 6))
        expect(flat < par, f"{name}: flatness ({flat:.3f}) < parallelism to A ({par:.3f}): a free zone is never wider",
               (round(flat, 4), round(par, 4)))
        expect(c["0000001c"].get("Constraint.reference") == "1" and c["00000025"].get("Constraint.reference") == "1",
               f"{name}: both values are reference dimensions, written back by regenerate")
        z1 = slvs.act_point(e, "00100001"), slvs.act_point(e, "00100002")
        slope = (z1[1][1] - z1[0][1]) / (z1[1][0] - z1[0][0])
        expect(abs(slope) > 1e-4, f"{name}: the flatness zone tilted to fit (slope {slope:.5f}); the parallelism zone may not")
    src = slvs.params(ctx.here / "surface.slvs")["00100014"]
    out = slvs.act_point(slvs.entities(ctx.out / "surface.slvs"), "00100002")[1]
    expect(not close(src, out), "zone line end solved away from its initial guess", (src, round(out, 5)))
