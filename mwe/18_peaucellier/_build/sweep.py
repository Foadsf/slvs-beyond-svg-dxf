"""Regenerate every pose with SolveSpace, then render only measured coordinates.

Python standard library only. Run from any directory with --cli PATH.
SPDX-License-Identifier: CC-BY-SA-4.0
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import slvs
from build import find_cli

spec = importlib.util.spec_from_file_location("peau_check", HERE / "check.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def run_cli(cli, *args):
    result = subprocess.run([str(cli), *map(str, args)], capture_output=True,
                            text=True, timeout=45)
    log = result.stdout + result.stderr
    version_only = args == ("version",) and log.strip().startswith("SolveSpace version ")
    if (result.returncode and not version_only) or any(s in log for s in ("Error:", "Cannot load", "failed")):
        raise RuntimeError(log)
    return log


def replace_value(data, handle, value):
    chunks = data.split(b"AddConstraint")
    hits = 0
    for i, chunk in enumerate(chunks):
        if ("Constraint.h.v=" + handle + "\n").encode() in chunk:
            lines = chunk.splitlines(keepends=True)
            found = False
            for j, line in enumerate(lines):
                if line.startswith(b"Constraint.valA="):
                    lines[j] = f"Constraint.valA={value:g}\n".encode()
                    found = True
            if not found:  # SolveSpace omits zero/default values on save.
                lines.append(f"Constraint.valA={value:g}\n".encode())
            hits += 1
            chunks[i] = b"".join(lines)
    if hits != 1:
        raise ValueError(f"expected exactly one value for constraint {handle}, got {hits}")
    return b"AddConstraint".join(chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli")
    args = parser.parse_args()
    cli = find_cli(args.cli)
    source = (HERE / "linkage.slvs").read_bytes()
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    rows, frames = [], []
    logs = []
    for label, crank in [("nominal", 35), ("broken", 36)]:
        folder = out / label
        folder.mkdir(exist_ok=True)
        seed = source
        # Follow the same assembly branch from the base pose in both directions.
        # A large independent jump can fold Q onto P while all bar lengths pass.
        for height in list(range(10, -31, -1)) + list(range(11, 31)):
            if height == 11:
                seed = source
            data = replace_value(seed, "00000015", -height)
            if crank != 35:
                data = replace_value(data, "00000014", crank)
            path = folder / f"pose_{height + 30:03d}.slvs"
            path.write_bytes(data)
            logs.append(run_cli(cli, "regenerate", path))
            seed = path.read_bytes()
            p = checks.points(slvs, path)
            m = checks.measurements(p, height, crank)
            if not checks.valid(m, straight=crank == 35):
                raise AssertionError(f"{label} h={height}: native geometry invalid: {m}")
            rows.append({"case": label, "input_y_mm": height,
                         "output_x_mm": p["Q"][0], "output_y_mm": p["Q"][1], **m})
            if label == "nominal":
                frames.append({"height": height, "points": p})
        print(f"{label}: 61 native poses regenerated and checked", flush=True)
    frames.sort(key=lambda frame: frame["height"])
    rows.sort(key=lambda row: (row["case"], row["input_y_mm"]))
    good = [r for r in rows if r["case"] == "nominal"]
    bad = [r for r in rows if r["case"] == "broken"]
    error = max(r["straight_error_mm"] for r in good)
    bad_error = max(r["straight_error_mm"] for r in bad)
    bad_drift = max(r["output_x_mm"] for r in bad) - min(r["output_x_mm"] for r in bad)
    if bad_error < 0.1 or bad_drift < 0.1 or any(checks.valid(checks.measurements(
            checks.points(slvs, out / "broken" / f"pose_{i:03d}.slvs"), i - 30, 36))
            for i in range(61)):
        raise AssertionError("broken crank did not fail the straight-line check")
    summary = dict(cli_version=run_cli(cli, "version").strip(), poses=61,
                   source_sha256=hashlib.sha256(source).hexdigest(),
                   max_straight_error_mm=error,
                   stroke_mm=max(r["output_y_mm"] for r in good)-min(r["output_y_mm"] for r in good),
                   negative_control=dict(crank_mm=36, rejected_poses=61,
                                         max_error_mm=bad_error, lateral_drift_mm=bad_drift))
    with (out / "measurements.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out / "evidence.json").write_text(json.dumps(summary, indent=2) + "\n")
    # Keep logs local: their file paths identify the workstation.
    (out / "regenerate.log").write_text("".join(logs), encoding="utf-8")
    template = (HERE / "_build" / "motion.html").read_text(encoding="utf-8")
    (out / "motion.html").write_text(template.replace("__FRAMES__", json.dumps(frames))
                                    .replace("__SUMMARY__", json.dumps(summary)), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
