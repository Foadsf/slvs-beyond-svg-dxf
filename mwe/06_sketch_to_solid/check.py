"""Checks for 06_sketch_to_solid.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import re


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, depth in (("plate.slvs", 8.0), ("plate.depth20.slvs", 20.0)):
        out = ctx.out / name
        e = slvs.entities(out)
        hole = slvs.act_point(e, "00080001")
        expect(close(hole[0], 30) and close(hole[1], 30), f"{name}: hole centre 30 from left and bottom edges", hole[:2])
        top = slvs.act_point(e, "80030005")
        expect(close(top[2], depth), f"{name}: extruded copy of the origin corner at z = {depth:g}", top)
        (x0, x1), (y0, y1), (z0, z1) = ctx.stl_bbox(out.with_suffix(".stl"))
        expect(close(x1 - x0, 100) and close(y1 - y0, 60) and close(z0, 0) and close(z1, depth),
               f"{name}: STL bounding box 100 x 60 x {depth:g}", (x1 - x0, y1 - y0, z1 - z0))
        step = out.with_suffix(".step").read_text(errors="replace")
        n_surf = len(re.findall(r"B_SPLINE_SURFACE_WITH_KNOTS", step))
        expect(step.startswith("ISO-10303-21;") and n_surf >= 7,
               f"{name}: STEP is an ISO 10303-21 B-rep with >= 7 surfaces (6 faces + hole)", n_surf)
    src = slvs.params(ctx.here / "plate.slvs")["80030002"]
    out = slvs.params(ctx.out / "plate.slvs")["80030002"]
    expect(close(out, 4.0) and not close(src, out),
           "extrusion parameter solved to depth/2 from the distance constraint (source guess differs)", (src, out))
