"""Checks for 16_gdt_coaxiality_runout.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, ecc in (("runout.slvs", 0.05), ("runout.e12.slvs", 0.12)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        p = slvs.params(out)
        dc, fc = slvs.act_point(e, "00040001"), slvs.act_point(e, "00050001")
        r = p["00050040"]
        expect(close(dc[0], 0) and close(dc[1], 0) and close(fc[0], ecc) and close(fc[1], 0),
               f"{name}: datum axis at origin, feature axis measured at ({ecc:g}, 0)", (dc[:2], fc[:2]))
        q1, q2 = slvs.act_point(e, "00060001"), slvs.act_point(e, "00060002")
        near, far = sorted(math.hypot(q[0], q[1]) for q in (q1, q2))
        expect(close(near, r - ecc, 1e-9) and close(far, r + ecc, 1e-9),
               f"{name}: indicator readings r-e / r+e along the line of centres", (round(near, 4), round(far, 4)))
        fim = float(c["0000000d"]["Constraint.valA"])
        expect(close(fim, 2 * ecc, 1e-9), f"{name}: circular runout FIM (LENGTH_DIFFERENCE reference) = 2e = {2 * ecc:g}", round(fim, 6))
        expect(close(float(c["0000000e"]["Constraint.valA"]), ecc, 1e-9), f"{name}: axis offset reference = e = {ecc:g}")
        expect(c["0000000d"].get("Constraint.reference") == "1", f"{name}: FIM is a reference (measured) dimension")
    for name, left in (("symmetry.slvs", 24.03), ("symmetry.off08.slvs", 24.08)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        cl = slvs.act_point(e, "00080001"), slvs.act_point(e, "00080002")
        ml = slvs.act_point(e, "000d0001"), slvs.act_point(e, "000d0002")
        expect(close(cl[0][0], 30) and close(cl[1][0], 30), f"{name}: datum centre plane at x = 30 from two midpoints", (cl[0][0], cl[1][0]))
        off = left + 6 - 30
        expect(close(ml[0][0], 30 + off, 1e-9) and close(ml[1][0], 30 + off, 1e-9), f"{name}: slot median plane at x = {30 + off:.2f}", ml[0][0])
        sym = abs(float(c["0000001c"]["Constraint.valA"]))
        expect(close(sym, abs(off), 1e-9), f"{name}: median offset reference = {abs(off):.2f}; symmetry zone needed = {2 * abs(off):.2f}"
               + (" (ACCEPT at 0.1)" if 2 * abs(off) <= 0.1 else " (REJECT at 0.1)"), round(sym, 6))
    src = slvs.params(ctx.here / "runout.slvs")["00060010"]
    out = slvs.act_point(slvs.entities(ctx.out / "runout.slvs"), "00060001")[0]
    expect(not close(src, out), "indicator line end solved away from its initial guess", (src, round(out, 5)))
