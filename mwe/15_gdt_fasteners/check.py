"""Checks for 15_gdt_fasteners.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math

F = 6.0   # fastener MMC


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, H in (("fastener.slvs", 6.4), ("fastener.h66.slvs", 6.6)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        p = slvs.params(out)
        t_float = float(c["0000000d"]["Constraint.valA"])
        t_fixed = float(c["0000000e"]["Constraint.valA"])
        expect(close(t_float, H - F, 1e-9), f"{name}: floating-fastener T = H - F = {H - F:.2f} (pure geometry)", round(t_float, 6))
        expect(close(t_fixed, (H - F) / 2, 1e-9), f"{name}: fixed-fastener T = (H - F)/2 = {(H - F) / 2:.2f} (midpoint)", round(t_fixed, 6))
        rH, rF = p["00100040"], p["00130040"]
        expect(close(2 * rH, H, 1e-9) and close(2 * rF, F, 1e-9), f"{name}: hole and bolt diameters tied to H and F", (2 * rH, 2 * rF))
        hc, bc = slvs.act_point(e, "00100001"), slvs.act_point(e, "00130001")
        d = math.hypot(hc[0] - bc[0], hc[1] - bc[1])
        expect(close(d, rH - rF, 1e-9), f"{name}: worst case: centre distance {d:.4f} == rH - rF: bolt internally tangent", round(d, 6))
        expect(close(float(c["0000002a"]["Constraint.valA"]), d, 1e-9), f"{name}: centre distance written as reference")
        tp = slvs.act_point(e, "000a0000")
        expect(close(hc[0] - tp[0], t_fixed / 2, 1e-9) and close(tp[0] - bc[0], t_fixed / 2, 1e-9),
               f"{name}: each axis offset by T_fixed/2 = {t_fixed / 2:.3f} in opposite directions (LENGTH_RATIO 0.5)")
        expect(close(2 * p["000b0040"], t_fixed, 1e-9) and close(2 * p["000d0040"], t_float, 1e-9),
               f"{name}: zone circles Ø{t_fixed:.2f} (fixed) and Ø{t_float:.2f} (floating) via EQUAL_LENGTH_LINES")
    src = slvs.params(ctx.here / "fastener.slvs")["000b0040"]
    out = slvs.params(ctx.out / "fastener.slvs")["000b0040"]
    expect(not close(src, out), "fixed-zone radius solved away from its initial guess", (src, out))
