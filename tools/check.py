"""Verify that every MWE solved to the geometry its README claims.

Run ``python tools/build.py`` first.  Each ``mwe/NN_name/check.py`` defines
``run(ctx)`` and reads the regenerated files in its own ``out/`` directory
(plus exported STL/STEP where relevant).  ``ctx`` offers:

    ctx.here      Path of the MWE directory
    ctx.out       Path of its out/ directory
    ctx.slvs      the tools/slvs.py module
    ctx.expect(cond, what, got=None)
    ctx.close(a, b, tol=1e-6)
    ctx.stl_bbox(path) -> ((x0,x1),(y0,y1),(z0,z1))
    ctx.sha(path)

Every check compares a *solved* value (``Entity.actPoint`` or ``Param.val``
written back by ``solvespace-cli regenerate``) against a value derived from
the constraints alone, and asserts the solved value differs from the initial
guess in the source, so a build that silently skipped solving cannot pass.

Usage: python tools/check.py [--only 14]

SPDX-License-Identifier: CC-BY-SA-4.0
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MWE = ROOT / "mwe"
sys.path.insert(0, str(HERE))
import slvs  # noqa: E402

TOL = 1e-6


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def stl_bbox(path: Path):
    """Bounding box of a binary STL (what solvespace-cli export-mesh writes)."""
    data = Path(path).read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    xs, ys, zs = [], [], []
    for i in range(n):
        v = struct.unpack("<12f", data[84 + i * 50: 84 + i * 50 + 48])
        for k in range(3):
            xs.append(v[3 + 3 * k]); ys.append(v[4 + 3 * k]); zs.append(v[5 + 3 * k])
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_ctx(mwe: Path, failures: list[str]) -> SimpleNamespace:
    def expect(cond: bool, what: str, got=None) -> None:
        mark = "ok  " if cond else "FAIL"
        tail = "" if got is None else f"   [{got}]"
        print(f"  {mark} {what}{tail}")
        if not cond:
            failures.append(f"{mwe.name}: {what}")
    return SimpleNamespace(here=mwe, out=mwe / "out", slvs=slvs, expect=expect,
                           close=close, stl_bbox=stl_bbox, sha=sha)


def load_check(mwe: Path):
    spec = importlib.util.spec_from_file_location(f"check_{mwe.name}", mwe / "check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="check only MWE directories whose name starts with this")
    args = ap.parse_args()

    failures: list[str] = []
    ran = 0
    for mwe in sorted(MWE.iterdir()):
        if not (mwe / "check.py").exists():
            continue
        if args.only and not mwe.name.startswith(args.only):
            continue
        print(mwe.name)
        if not (mwe / "out").exists():
            failures.append(f"{mwe.name}: no out/ directory; run tools/build.py first")
            print("  FAIL no out/ directory; run tools/build.py first")
            continue
        try:
            load_check(mwe).run(make_ctx(mwe, failures))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{mwe.name}: exception {exc!r}")
            print(f"  FAIL exception: {exc!r}")
        ran += 1
    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"all checks passed ({ran} MWEs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
