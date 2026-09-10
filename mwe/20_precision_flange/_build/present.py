"""Derive the offline model review from regenerated geometry and native PMI.

SPDX-License-Identifier: CC-BY-SA-4.0
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parents[1]/"tools"))
import slvs
import pmi


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = HERE/"out"
    assoc = json.loads((HERE/"associations.json").read_text())
    models = []
    for name in ("flange","flange.t18"):
        native = out/f"{name}.slvs"
        annotations = pmi.extract(native)
        entities = slvs.entities(native)
        def point(h):
            return list(slvs.act_point(entities,h))
        d = (out/f"{name}.stl").read_bytes()
        count = struct.unpack_from("<I",d,80)[0]
        assert len(d)==84+50*count
        triangles = [list(struct.unpack_from("<12f",d,84+i*50))[3:] for i in range(count)]
        notes = {n["handle"]:n for n in annotations["notes"]}
        text = notes[assoc["position_note"]]["text"]
        mmc,lmc,tol = map(float,re.search(r"DIA ([\d.]+)-([\d.]+) THRU; \[POS\|DIA ([\d.]+) \(M\)",text).groups())
        t = next(d["value"] for d in annotations["dimensions"] if d["handle"]==assoc["thickness_constraint"])
        models.append(dict(name=name,thickness=t,triangles=triangles,pmi=annotations,
                           pilot=point(assoc["boss_top"]), holes=[point(h) for h in assoc["hole_tops"]],
                           inspection=dict(mmc=mmc,lmc=lmc,position_at_mmc=tol,virtual_condition=mmc-tol),
                           hashes={ext:sha(out/f"{name}.{ext}") for ext in ("slvs","step","stl")},
                           source_hash=sha(HERE/f"{name}.slvs")))
    data=dict(part="PF-020",revision="A",units="mm",models=models)
    (out/"definition.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    template=(HERE/"_build/review.html").read_text(encoding="utf-8")
    (out/"review.html").write_text(template.replace("__MODEL_DATA__",json.dumps(data,separators=(",",":"))),encoding="utf-8")
    print(f"Derived offline review and definition.json from {len(models)} native models.")


if __name__=="__main__":
    main()
