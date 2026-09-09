"""Checks for 02_tangent_slot.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import math
import re


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, pitch in (("slot.slvs", 60.0), ("slot.pitch90.slvs", 90.0)):
        out = ctx.out / name
        e = slvs.entities(out)
        lc, ls, le = (slvs.act_point(e, h) for h in ("00040001", "00040002", "00040003"))
        rc, rs, re_ = (slvs.act_point(e, h) for h in ("00050001", "00050002", "00050003"))
        expect(close(rc[0] - lc[0], pitch) and close(rc[1], 0.0),
               f"{name}: arc centres {pitch:g} apart on the horizontal", (rc[0] - lc[0], rc[1]))
        for label, p in (("L start", ls), ("L end", le), ("R start", rs), ("R end", re_)):
            cx = lc[0] if label[0] == "L" else rc[0]
            expect(close(abs(p[1]), 10.0) and close(math.hypot(p[0] - cx, p[1]), 10.0),
                   f"{name}: {label} sits on its circle at y = +-10 (tangent point)",
                   (round(p[0], 6), round(p[1], 6)))
        top = (slvs.act_point(e, "00060001"), slvs.act_point(e, "00060002"))
        bot = (slvs.act_point(e, "00070001"), slvs.act_point(e, "00070002"))
        expect(close(top[0][1], top[1][1]) and close(bot[0][1], bot[1][1]),
               f"{name}: both straight edges came out horizontal without a HORIZONTAL constraint")
        expect(close(top[1][0] - top[0][0], pitch), f"{name}: straight edge length equals pitch",
               top[1][0] - top[0][0])
    dxf = (ctx.out / "slot.dxf").read_text(errors="replace")
    n_line = len(re.findall(r"^LINE\r?$", dxf, re.M))
    expect(n_line == 2, "DXF export has exactly 2 LINEs: the construction centre line is not exported", n_line)
