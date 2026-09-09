"""Checks for 17_gdt_profile.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math

R, C = 10.0, (30.0, 30.0)   # nominal arc radius and centre


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, tol in (("profile.slvs", 0.5), ("profile.tol1.slvs", 1.0)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        h = tol / 2
        T = float(c["0000000d"]["Constraint.valA"])
        expect(close(T, tol), f"{name}: the single tolerance number is {tol:g}", T)
        o1 = slvs.act_point(e, "000a0001"), slvs.act_point(e, "000a0002")
        i1 = slvs.act_point(e, "000d0001"), slvs.act_point(e, "000d0002")
        o2 = slvs.act_point(e, "000c0001"), slvs.act_point(e, "000c0002")
        i2 = slvs.act_point(e, "000f0001"), slvs.act_point(e, "000f0002")
        expect(all(close(pt[1], 20 - h, 1e-7) for pt in o1) and all(close(pt[1], 20 + h, 1e-7) for pt in i1),
               f"{name}: straight boundaries at y = 20 -/+ {h:g} (one EQ_LEN_PT_LINE_D each, no literal)", (o1[0][1], i1[0][1]))
        expect(all(close(pt[0], 40 + h, 1e-7) for pt in o2) and all(close(pt[0], 40 - h, 1e-7) for pt in i2),
               f"{name}: vertical boundaries at x = 40 +/- {h:g}, derived from tangency alone", (o2[0][0], i2[0][0]))
        for arc, sign, label in (("000b", +1, "outer"), ("000e", -1, "inner")):
            s, en = slvs.act_point(e, arc + "0002"), slvs.act_point(e, arc + "0003")
            rs, re_ = (math.hypot(q[0] - C[0], q[1] - C[1]) for q in (s, en))
            expect(close(rs, R + sign * h, 1e-7) and close(re_, R + sign * h, 1e-7),
                   f"{name}: {label} arc concentric, radius {R + sign * h:g}", (round(rs, 6), round(re_, 6)))
        expect(close(float(c["00000025"]["Constraint.valA"]), 2 * (R + h), 1e-6) and close(float(c["00000026"]["Constraint.valA"]), 2 * (R - h), 1e-6),
               f"{name}: reference diameters written as {2 * (R + h):g} and {2 * (R - h):g}")
        expect(close(float(c["00000027"]["Constraint.valA"]), h, 1e-7) and close(float(c["0000002a"]["Constraint.valA"]), h, 1e-7),
               f"{name}: offset references {h:g} on both straight legs")
    src = slvs.params(ctx.here / "profile.slvs")["000b0016"]
    out = slvs.act_point(slvs.entities(ctx.out / "profile.slvs"), "000b0003")[0]
    expect(not close(src, out), "outer arc end solved away from its initial guess", (src, round(out, 5)))
