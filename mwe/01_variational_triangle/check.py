"""Checks for 01_variational_triangle.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    src_guess = slvs.params(ctx.here / "triangle.slvs")["00050014"]      # apex v, initial guess
    for name, hyp in (("triangle.slvs", 125.0), ("triangle.hyp200.slvs", 200.0)):
        out = ctx.out / name
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
