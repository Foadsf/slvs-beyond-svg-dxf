"""Checks for 19_mbd_pmi.  SPDX-License-Identifier: CC-BY-SA-4.0"""
import json
import math
import re

DERIVED = ("svg", "dxf", "png", "top.svg", "top.png", "right.svg", "right.png",
           "iso.svg", "iso.png", "step", "stl", "pmi.json")


def run(ctx):
    slvs, expect, close = ctx.slvs, ctx.expect, ctx.close
    for name, t in (("plate", 8.0), ("plate.t12", 12.0)):
        out = ctx.out / (name + ".slvs")
        e = slvs.entities(out)
        pmi = json.loads((ctx.out / (name + ".pmi.json")).read_text(encoding="utf-8"))
        dims = {d["handle"]: d for d in pmi["dimensions"]}

        missing = [ext for ext in DERIVED if not (ctx.out / f"{name}.{ext}").exists()]
        expect(not missing, f"{name}: every derived artefact exists (3 views, iso, STEP, STL, DXF, PMI)", missing or "all")

        # the model is the definition: thickness is a driving 3D dimension, and the solid follows it
        expect(close(dims["0000000f"]["value"], t) and not dims["0000000f"]["reference"],
               f"{name}: driving thickness dimension {t:g} lives on the 3D model", dims["0000000f"]["value"])
        (_, _), (_, _), (z0, z1) = ctx.stl_bbox(ctx.out / (name + ".stl"))
        expect(close(z1 - z0, t), f"{name}: STL thickness equals the PMI value", z1 - z0)

        # 3D reference PMI repeats the sketch's driving values: model and annotation cannot disagree
        pairs = {"00000019": ("0000000a", "width 60"), "0000001a": ("0000000b", "height 40"),
                 "0000001b": ("0000000e", "hole Ø10"), "0000001c": ("0000000d", "hole from B 20"),
                 "0000001d": ("0000000c", "hole from C 20")}
        for ref, (drv, label) in pairs.items():
            expect(dims[ref]["reference"] and dims[ref]["in_3d"] and not dims[drv]["reference"]
                   and close(abs(dims[ref]["value"]), abs(dims[drv]["value"]), 1e-6),
                   f"{name}: 3D reference {label} == sketch driving value", (dims[ref]["value"], dims[drv]["value"]))
        diag = dims["00000010"]["value"]
        expect(close(diag, math.hypot(60, 40, t), 1e-6), f"{name}: space diagonal reference = sqrt(60²+40²+{t:g}²)", round(diag, 4))

        # anchored PMI follows the geometry it is attached to
        hole_top = slvs.act_point(e, "8003002a")
        expect(close(hole_top[2], t) and all(n["anchor_xyz"] == [20.0, 20.0, t] for n in pmi["notes"] if n["anchor"]),
               f"{name}: hole callout and FCF anchored to the hole axis on the top face (20, 20, {t:g})")
        expect(sorted(d["datum"] for d in pmi["datums"]) == ["A", "B", "C"]
               and all(d["anchor_xyz"] is not None for d in pmi["datums"]),
               f"{name}: datums A, B, C present and anchored to model points")
        texts = " ".join(n["text"] for n in pmi["notes"])
        expect("REV B" in texts and "MATERIAL" in texts and "Ra 3.2" in texts,
               f"{name}: part number, revision, material and finish travel with the model")

        # what the exchange formats carry: measured, not assumed
        step = (ctx.out / (name + ".step")).read_text(errors="replace")
        n_pmi = len(re.findall(r"DRAUGHTING|GEOMETRIC_TOLERANCE|DIMENSIONAL_SIZE|DATUM|ANNOTATION", step))
        expect("CONFIG_CONTROL_DESIGN" in step and n_pmi == 0,
               f"{name}: STEP is AP203 geometry only, zero PMI entities (no AP242 semantic PMI)", n_pmi)
        dxf = (ctx.out / (name + ".dxf")).read_text(errors="replace")
        n_text = len(re.findall(r"^TEXT\r?$", dxf, re.M))
        n_dim = len(re.findall(r"^DIMENSION\r?$", dxf, re.M))
        expect(n_text >= 8 and n_dim >= 1, f"{name}: DXF front view carries the notes as TEXT and dimensions as DIMENSION", (n_text, n_dim))

    src = slvs.params(ctx.here / "plate.slvs")["80030002"]
    out = slvs.params(ctx.out / "plate.slvs")["80030002"]
    expect(not close(src, out) and close(out, 4.0), "extrusion parameter solved from the thickness PMI, not from its guess", (src, out))
    a = json.loads((ctx.out / "plate.pmi.json").read_text(encoding="utf-8"))
    b = json.loads((ctx.out / "plate.t12.pmi.json").read_text(encoding="utf-8"))
    changed = [d["handle"] for d, d2 in zip(a["dimensions"], b["dimensions"]) if not close(d["value"], d2["value"], 1e-6)]
    expect(changed == ["0000000f", "00000010"], "between the variants only the thickness and the diagonal changed", changed)
