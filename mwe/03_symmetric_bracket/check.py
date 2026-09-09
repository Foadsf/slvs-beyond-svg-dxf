"""Checks for 03_symmetric_bracket.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, top in (("bracket.slvs", 40.0), ("bracket.top70.slvs", 70.0)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        tl, tr = slvs.act_point(e, "00060002"), slvs.act_point(e, "00050002")
        expect(close(tl[0], 50 - top / 2) and close(tr[0], 50 + top / 2) and close(tl[1], 60) and close(tr[1], 60),
               f"{name}: top corners mirrored about x=50, {top:g} apart, at height 60", (tl[:2], tr[:2]))
        side = float(c["0000000e"]["Constraint.valA"])
        expect(close(side, math.hypot(50 - top / 2, 60), 1e-4),
               f"{name}: reference side length rewritten to sqrt(({50 - top / 2:g})^2 + 60^2)", f"{side:.4f}")
