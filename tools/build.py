"""Build every MWE: regenerate the hand-written ``.slvs`` sources with
``solvespace-cli`` and export SVG / DXF / PNG (and STEP / STL for 3D ones).

Usage::

    python tools/build.py [--cli PATH] [--only 01] [--verbose]

The CLI is found from ``--cli``, then ``$SOLVESPACE_CLI``, then ``PATH``.

Each MWE directory contains a ``build.json``::

    {
      "order":   ["skeleton.slvs", "bracket.slvs"],   # regenerate in this order
      "view":    "front",                              # export-view / thumbnail direction
      "exports": ["svg", "dxf", "png"],                # 2D exports for every file
      "solid":   ["bracket.slvs"]                      # also export-surfaces (STEP) + export-mesh (STL)
    }

Outputs go to ``<mwe>/out/``.  Sources are never modified: they are copied
into ``out/`` first, and ``regenerate`` rewrites the *copy* with solved values.
Order matters for transclusion: a linked (master) file is read by the
downstream file at the *entity* level, so the master must be regenerated
before anything that links it.

SPDX-License-Identifier: CC-BY-SA-4.0
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MWE_DIR = ROOT / "mwe"
sys.path.insert(0, str(HERE))
import slvs  # noqa: E402

GENERATED_SUFFIXES = (".slvs", ".svg", ".dxf", ".png", ".step", ".stl")


def find_cli(explicit: str | None) -> Path:
    candidates = [explicit, os.environ.get("SOLVESPACE_CLI"),
                  shutil.which("solvespace-cli"), shutil.which("solvespace-cli.exe")]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c).resolve()
    sys.exit("solvespace-cli not found: pass --cli PATH or set SOLVESPACE_CLI. "
             "See README.md, section 'Getting solvespace-cli'.")


def run(cli: Path, *args: str, verbose: bool = False) -> None:
    """Run one CLI command and fail loudly.

    The CLI prints ``Written '<file>'.`` even when the write failed (it also
    prints ``Error: Couldn't write``), and its exit code is 0 in that case.
    So we treat any ``Error:`` on stderr as a failure and, for outputs, the
    caller stats the file afterwards.
    """
    cmd = [str(cli), *args]
    if verbose:
        print("  $", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    err = proc.stderr.strip()
    if verbose and err:
        print("   ", err.replace("\n", "\n    "))
    if proc.returncode != 0 or "Error:" in err or "Cannot load" in err:
        raise RuntimeError(f"solvespace-cli failed ({proc.returncode}):\n  {' '.join(cmd)}\n  {err}")


def expect_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"expected output missing or empty: {path}")


def build_one(cli: Path, mwe: Path, verbose: bool) -> list[Path]:
    spec = json.loads((mwe / "build.json").read_text(encoding="utf-8"))
    out = mwe / "out"
    out.mkdir(exist_ok=True)
    for old in out.rglob("*"):
        if old.is_file() and old.suffix in GENERATED_SUFFIXES:
            old.unlink()

    produced: list[Path] = []
    view = spec.get("view", "front")
    exports = spec.get("exports", ["svg", "dxf", "png"])
    solids = set(spec.get("solid", []))

    for name in spec["order"]:
        src = mwe / name                 # may live in a sub-folder, e.g. base/skeleton.slvs
        dst = out / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        slvs.fix_magic(dst)          # tolerate a UTF-8-mangled header in a source
        run(cli, "regenerate", str(dst), verbose=verbose)
        expect_file(dst)
        produced.append(dst)

        # The output pattern must be a bare "%.<ext>": "%" expands to the input
        # path *without extension but with its directories*, so prefixing a
        # directory yields "dir/dir/name.ext" (measured, see README).
        for ext in exports:
            target = dst.with_suffix("." + ext)
            if ext == "png":
                run(cli, "thumbnail", "--view", view, "--size", "800x600",
                    "--output", "%.png", str(dst), verbose=verbose)
            else:
                run(cli, "export-view", "--view", view, "--bg-color", "off",
                    "--output", f"%.{ext}", str(dst), verbose=verbose)
            expect_file(target)
            produced.append(target)

        if name in solids:
            run(cli, "export-surfaces", "--output", "%.step", str(dst), verbose=verbose)
            expect_file(dst.with_suffix(".step"))
            run(cli, "export-mesh", "--chord-tol", "0.1", "--output", "%.stl", str(dst),
                verbose=verbose)
            expect_file(dst.with_suffix(".stl"))
            iso_svg = dst.parent / (dst.stem + ".iso.svg")
            run(cli, "export-view", "--view", "isometric", "--bg-color", "off",
                "--output", "%.iso.svg", str(dst), verbose=verbose)
            expect_file(iso_svg)
            iso_png = dst.parent / (dst.stem + ".iso.png")
            run(cli, "thumbnail", "--view", "isometric", "--size", "800x600",
                "--output", "%.iso.png", str(dst), verbose=verbose)
            expect_file(iso_png)
            produced += [dst.with_suffix(".step"), dst.with_suffix(".stl"), iso_svg, iso_png]
    return produced


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cli", help="path to solvespace-cli")
    ap.add_argument("--only", help="build only MWE directories whose name starts with this")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    cli = find_cli(args.cli)
    ver = subprocess.run([str(cli), "version"], capture_output=True, text=True).stderr.strip()
    print(f"using {cli}\n  {ver}")

    failures = 0
    for mwe in sorted(MWE_DIR.iterdir()):
        if not (mwe / "build.json").exists():
            continue
        if args.only and not mwe.name.startswith(args.only):
            continue
        try:
            produced = build_one(cli, mwe, args.verbose)
            print(f"ok    {mwe.name}: {len(produced)} files in out/")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL  {mwe.name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
