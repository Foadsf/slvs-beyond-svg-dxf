"""Checks for 14_gdt_position_mmc.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math

MMC, TOL, VC = 10.0, 0.5, 9.5
ACTUAL_CENTRE = (40.15, 25.10)


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, dia in (("hole.slvs", 10.2), ("hole.mmc.slvs", 10.0)):
        out = ctx.out / name
        e = slvs.entities(out)
        c = slvs.constraints(out)
        p = slvs.params(out)
        tp = slvs.act_point(e, "00080001")
        hc = slvs.act_point(e, "00090001")
        expect(close(tp[0], 40) and close(tp[1], 25), f"{name}: true position from basic dimensions (40, 25)", tp[:2])
        expect(close(hc[0], ACTUAL_CENTRE[0]) and close(hc[1], ACTUAL_CENTRE[1]),
               f"{name}: measured hole centre pinned at {ACTUAL_CENTRE}", hc[:2])
        dev = float(c["00000019"]["Constraint.valA"])
        zone = float(c["0000001a"]["Constraint.valA"])
        bonus = dia - MMC
        expect(close(dev, math.hypot(0.15, 0.10), 1e-6), f"{name}: radial deviation reference = hypot(0.15, 0.10)", round(dev, 5))
        expect(close(zone, TOL + bonus, 1e-6), f"{name}: zone diameter = {TOL} + bonus {bonus:g} = {TOL + bonus:g} (LENGTH_DIFFERENCE)",
               round(zone, 5))
        expect(close(2 * p["00090040"], dia), f"{name}: actual hole diameter {dia:g}", 2 * p["00090040"])
        expect(2 * dev <= zone, f"{name}: position error diameter {2 * dev:.4f} <= zone {zone:.2f}: ACCEPT (margin {zone - 2 * dev:.4f})")
        expect(close(2 * p["000c0040"], VC), f"{name}: virtual-condition gauge circle diameter {VC}", 2 * p["000c0040"])
        expect(dev + VC / 2 <= dia / 2 + 1e-9, f"{name}: gauge pin clears the actual hole: {dev:.4f} + {VC/2} <= {dia/2}")
    src = slvs.params(ctx.here / "hole.slvs")["00080040"]
    out = slvs.params(ctx.out / "hole.slvs")["00080040"]
    expect(not close(src, out) and close(out, 0.35), "zone radius solved to 0.35 from a different initial guess", (src, out))
