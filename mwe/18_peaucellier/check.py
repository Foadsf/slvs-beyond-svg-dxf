"""Independent geometry checks for the native Peaucellier mechanism."""
import math

JOINTS = dict(O="00040001", C="00040002", A="00050002",
              B="00060002", P="00070002", Q="00090002")
BAR_PAIRS = [("O", "A"), ("O", "B"), ("A", "P"), ("P", "B"),
             ("B", "Q"), ("Q", "A"), ("C", "P")]


def points(slvs, path):
    entities = slvs.entities(path)
    return {name: slvs.act_point(entities, handle)[:2]
            for name, handle in JOINTS.items()}


def measurements(p, height, crank=35.0):
    """References follow from circle intersection and inversion, not seeds."""
    lengths = [100, 100, 60, 60, 60, 60, crank]
    errors = [abs(math.dist(p[a], p[b]) - length)
              for (a, b), length in zip(BAR_PAIRS, lengths)]
    expected_px = 35 + math.sqrt(crank**2 - height**2)
    k = 100**2 - 60**2
    px, py = p["P"]
    qx, qy = p["Q"]
    expected_q = (k * expected_px / (expected_px**2 + height**2),
                  k * height / (expected_px**2 + height**2))
    return {
        "bar_error_mm": max(errors),
        "ground_error_mm": max(math.dist(p["O"], (0, 0)),
                               math.dist(p["C"], (35, 0))),
        "drive_error_mm": abs(py - height),
        "branch_error_mm": abs(px - expected_px),
        "inverse_error_mm2": abs(math.hypot(px, py) * math.hypot(qx, qy) - k),
        "collinearity_error_mm2": abs(px * qy - py * qx),
        "output_error_mm": math.dist((qx, qy), expected_q),
        "straight_error_mm": abs(qx - k / 70),
    }


def valid(m, straight=True):
    return all(math.isfinite(v) and v <= (1e-4 if key.endswith("mm2") else 1e-6)
               for key, v in m.items() if straight or key != "straight_error_mm")


def run(ctx):
    for name, height in [("linkage.slvs", 10), ("linkage.height25.slvs", 25)]:
        p = points(ctx.slvs, ctx.out / name)
        m = measurements(p, height)
        ctx.expect(valid(m), f"{name}: bars, ground, input, branch and inversion", m)
        ctx.expect(ctx.close(p["Q"][0], 6400 / 70),
                   f"{name}: unconstrained output x = 6400/70 mm", p["Q"])
        src = ctx.slvs.params(ctx.here / name)
        ctx.expect(abs(src["00090010"] - ctx.slvs.params(ctx.out / name)["00090010"]) > 1,
                   "native solve moved the deliberately wrong seed")
    base = (ctx.here / "linkage.slvs").read_bytes()
    variant = (ctx.here / "linkage.height25.slvs").read_bytes()
    ctx.expect(base.replace(b"Constraint.valA=-10\n", b"Constraint.valA=-25\n") == variant,
               "source variant changes exactly one driving value")
    # Audit the actual constraint vocabulary: no line/slider constraint on Q.
    records = ctx.slvs.parse(ctx.here / "linkage.slvs")
    constraints = [r for r in records if r["_kind"] == "AddConstraint"]
    ctx.expect(len(constraints) == 21 and
               all(r["Constraint.type"] in {"20", "30", "80", "32"} for r in constraints) and
               all(r["Constraint.ptA.v"] == JOINTS["P"]
                   for r in constraints if r["Constraint.type"] == "32"),
               "only the input P has a point-to-line drive; no output straightness constraint")
    p = points(ctx.slvs, ctx.out / "linkage.slvs")
    p["Q"] = (p["Q"][0] + 0.1, p["Q"][1])
    ctx.expect(not valid(measurements(p, 10)), "negative control: displaced output rejected")
    p["Q"] = p["P"]
    folded = measurements(p, 10)
    ctx.expect(folded["bar_error_mm"] < 1e-6 and not valid(folded),
               "folded-branch control: all lengths pass, but inversion rejects Q=P")
