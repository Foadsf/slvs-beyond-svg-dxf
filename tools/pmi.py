"""Extract product and manufacturing information (PMI) from a regenerated ``.slvs``.

In a model-based definition the model is the dataset and the annotations
travel with it.  In SolveSpace those annotations are *constraints*:
driving dimensions (their ``valA``), reference dimensions (measured and
written back by ``regenerate``), and COMMENT constraints (notes, datum
labels, feature control frames written as text), optionally anchored to a
model point via ``ptA``.  This tool reads them back into JSON so a
downstream consumer (a CAM post, a QA sheet, a PLM importer) does not need
to parse the file format or render a drawing.

Usage::

    python tools/pmi.py out/plate.slvs            # prints JSON
    python tools/pmi.py out/plate.slvs -o plate.pmi.json

SPDX-License-Identifier: CC-BY-SA-4.0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slvs  # noqa: E402

DIMENSION_TYPES = {
    "30": "PT_PT_DISTANCE", "31": "PT_PLANE_DISTANCE", "32": "PT_LINE_DISTANCE",
    "33": "PT_FACE_DISTANCE", "34": "PROJ_PT_DISTANCE", "51": "LENGTH_RATIO",
    "56": "LENGTH_DIFFERENCE", "90": "DIAMETER", "120": "ANGLE",
}
GROUP_TYPES = {"5000": "DRAWING_3D", "5001": "DRAWING_WORKPLANE", "5100": "EXTRUDE",
               "5101": "LATHE", "5102": "REVOLVE", "5103": "HELIX", "5200": "ROTATE",
               "5201": "TRANSLATE", "5300": "LINKED"}


def _point(entities: dict, handle: str | None):
    if not handle or handle not in entities:
        return None
    x, y, z = slvs.act_point(entities, handle)
    return [round(x, 6), round(y, 6), round(z, 6)]


def extract(path: Path) -> dict:
    records = slvs.parse(path)
    entities = {r["Entity.h.v"]: r for r in records if r.get("_kind") == "AddEntity"}
    groups = [r for r in records if r.get("_kind") == "AddGroup"]
    out = {
        "source": Path(path).name,
        "units": "mm (SolveSpace stores lengths in millimetres; the file carries no unit field)",
        "groups": [{"handle": g["Group.h.v"], "name": g.get("Group.name", ""),
                    "type": GROUP_TYPES.get(g.get("Group.type", ""), g.get("Group.type", ""))}
                   for g in groups],
        "dimensions": [], "notes": [], "datums": [],
    }
    for r in records:
        if r.get("_kind") != "AddConstraint":
            continue
        typ = r.get("Constraint.type", "")
        group = r.get("Constraint.group.v", "")
        in_3d = "Constraint.workplane.v" not in r
        if typ == "1000":
            text = r.get("Constraint.comment", "").encode("latin-1").decode("utf-8", "replace")
            anchor = r.get("Constraint.ptA.v")
            note = {"handle": r["Constraint.h.v"], "text": text, "group": group, "in_3d": in_3d,
                    "anchor": anchor, "anchor_xyz": _point(entities, anchor)}
            if text.upper().startswith("DATUM "):
                note["datum"] = text.split()[1].strip(":")
                out["datums"].append(note)
            else:
                out["notes"].append(note)
        elif typ in DIMENSION_TYPES:
            refs = {k: r[k] for k in ("Constraint.ptA.v", "Constraint.ptB.v",
                                       "Constraint.entityA.v", "Constraint.entityB.v") if k in r}
            out["dimensions"].append({
                "handle": r["Constraint.h.v"], "type": DIMENSION_TYPES[typ],
                "value": float(r.get("Constraint.valA", "0")),
                "reference": r.get("Constraint.reference") == "1",
                "group": group, "in_3d": in_3d,
                "attached_to": {k.split(".")[1]: v for k, v in refs.items()},
                "point_xyz": {k.split(".")[1]: _point(entities, v) for k, v in refs.items()
                              if k.split(".")[1] in ("ptA", "ptB")},
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slvs", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    data = extract(args.slvs)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}: {len(data['dimensions'])} dimensions, "
              f"{len(data['notes'])} notes, {len(data['datums'])} datums")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
