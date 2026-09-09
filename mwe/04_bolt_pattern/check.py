"""Checks for 04_bolt_pattern.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, copies, step in (("flange.slvs", 5, 60.0), ("flange.8holes.slvs", 7, 45.0)):
        out = ctx.out / name
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
    src_angle = slvs.params(ctx.here / "flange.slvs")["80040003"]
    out_angle = slvs.params(ctx.out / "flange.slvs")["80040003"]
    expect(close(out_angle, math.radians(60) / 4) and not close(src_angle, out_angle),
           "rotation parameter solved from the ANGLE constraint (stored as angle/4 per copy)",
           (src_angle, out_angle))
