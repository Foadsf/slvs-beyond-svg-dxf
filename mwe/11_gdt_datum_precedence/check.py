"""Checks for 11_gdt_datum_precedence.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    hole = (40.0, 30.0)                      # measured hole centre (WHERE_DRAGGED)
    for name in ("plate.slvs", "plate.skew1.slvs"):
        out = ctx.out / name
        c = slvs.constraints(out)
        e = slvs.entities(out)
        theta = math.radians(float(c["0000000b"]["Constraint.valA"]))   # bottom-to-left-edge angle
        # datum simulators: A|B -> x from a line perpendicular to A through TL, y from A itself
        tl = slvs.act_point(e, "00070002")
        ab_x = hole[0] - tl[0]
        ab_y = hole[1]
        # B|A -> x from the left edge itself, y from a line perpendicular to B through BR
        b = (math.cos(theta), math.sin(theta))               # direction of the left edge from BL
        ba_x = abs(hole[0] * b[1] - hole[1] * b[0])
        ba_y = abs((hole[0] - 100.0) * b[0] + hole[1] * b[1])
        got = {k: abs(float(c[k]["Constraint.valA"])) for k in ("00000016", "00000017", "00000018", "00000019")}
        expect(close(tl[0], 60 * math.cos(theta), 1e-6) and close(tl[1], 60 * math.sin(theta), 1e-6),
               f"{name}: TL solved from the {math.degrees(theta):g} deg draft angle", tuple(round(v, 4) for v in tl[:2]))
        expect(close(got["00000016"], ab_y, 1e-6) and close(got["00000017"], ab_x, 1e-6),
               f"{name}: A|B frame reports ({ab_x:.4f}, {ab_y:.4f})", (got["00000017"], got["00000016"]))
        expect(close(got["00000018"], ba_x, 1e-6) and close(got["00000019"], ba_y, 1e-6),
               f"{name}: B|A frame reports ({ba_x:.4f}, {ba_y:.4f})", (got["00000018"], got["00000019"]))
        expect(abs(got["00000017"] - got["00000018"]) > 0.2 and abs(got["00000019"] - got["00000016"]) > 0.2,
               f"{name}: the two frames disagree by more than 0.2 on both coordinates",
               (round(got["00000017"] - got["00000018"], 4), round(got["00000019"] - got["00000016"], 4)))
        for k in got:
            expect(c[k].get("Constraint.reference") == "1", f"{name}: constraint {k[-2:]} is a reference dimension")
    src_tl_x = slvs.params(ctx.here / "plate.slvs")["00070013"]     # left edge, point 1 (TL), u
    out_tl = slvs.act_point(slvs.entities(ctx.out / "plate.slvs"), "00070002")
    expect(not close(src_tl_x, out_tl[0]), "TL's solved x differs from the initial guess in the source", (src_tl_x, out_tl[0]))
