"""Checks for 05_transclusion.  SPDX-License-Identifier: CC-BY-SA-4.0"""


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    expect(ctx.sha(ctx.here / "base" / "bracket.slvs") == ctx.sha(ctx.here / "variant" / "bracket.slvs"),
           "downstream bracket.slvs is byte-identical in base/ and variant/")
    for sub, pitch in (("base", 80.0), ("variant", 100.0)):
        out = ctx.out / sub / "bracket.slvs"
        e = slvs.entities(out)
        h1, h2 = slvs.act_point(e, "00080001"), slvs.act_point(e, "00090001")
        expect(close(h1[0], -pitch / 2) and close(h2[0], pitch / 2) and close(h1[1], 0) and close(h2[1], 0),
               f"{sub}: hole centres follow the linked skeleton pitch {pitch:g}", (h1[:2], h2[:2]))
        lo = slvs.act_point(e, "80030002")
        expect(all(close(v, 0) for v in lo), f"{sub}: linked skeleton origin pinned to the local origin", lo)
        g = [r for r in slvs.parse(out) if r.get("_kind") == "AddGroup" and r.get("Group.type") == "5300"][0]
        expect(g.get("Group.impFileRel") == "skeleton.slvs", f"{sub}: link is by relative path",
               g.get("Group.impFileRel"))
