"""Checks for 13_gdt_orientation.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math

TOL = 0.2   # the [..|0.2|A] in every feature control frame


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    cases = (("perpendicularity.slvs", "00050001", "00050002", 90.0, 40.0 * math.sin(math.radians(0.5))),
             ("angularity.slvs", "00050001", "00050002", 30.0, 40.0 * math.sin(math.radians(0.5))),
             ("parallelism.slvs", "00060001", "00060002", 0.0, 80.0 * math.tan(math.radians(0.5))))
    for name, f0, f1, basic, expected in cases:
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        p0, p1 = slvs.act_point(e, f0), slvs.act_point(e, f1)
        z = slvs.act_point(e, "00080001"), slvs.act_point(e, "00080002")
        dx, dy = z[1][0] - z[0][0], z[1][1] - z[0][1]
        zone_angle = math.degrees(math.atan2(dy, dx)) % 180
        dist = abs((p1[0] - z[0][0]) * dy - (p1[1] - z[0][1]) * dx) / math.hypot(dx, dy)
        ref = abs(float(c["00000012"]["Constraint.valA"]))
        expect(close(zone_angle % 180, basic % 180, 1e-6), f"{name}: zone boundary at the basic angle {basic:g} deg to A",
               round(zone_angle, 6))
        feat = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])) % 180
        expect(close(feat, (basic + 0.5) % 180, 1e-6), f"{name}: actual feature at basic + 0.5 deg", round(feat, 6))
        expect(close(ref, dist, 1e-6) and close(ref, expected, 1e-6),
               f"{name}: reference error = feature-end distance to zone boundary = {expected:.5f}", round(ref, 6))
        expect(ref > TOL, f"{name}: {ref:.3f} > {TOL} tolerance: the drawing reads REJECT", None)
        expect(c["00000012"].get("Constraint.reference") == "1", f"{name}: the error is a reference dimension")
    src = slvs.params(ctx.here / "perpendicularity.slvs")["00050013"]
    out = slvs.act_point(slvs.entities(ctx.out / "perpendicularity.slvs"), "00050002")[0]
    expect(not close(src, out), "feature end x solved away from its initial guess", (src, round(out, 5)))
