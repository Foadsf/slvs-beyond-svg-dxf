"""Offline tests for tools/slvs.py (no solvespace-cli needed).

SPDX-License-Identifier: CC-BY-SA-4.0
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import slvs  # noqa: E402

REAL = ROOT / "mwe" / "01_variational_triangle" / "triangle.slvs"


class MagicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_shipped_sources_have_raw_magic(self):
        bad = [p for p in (ROOT / "mwe").rglob("*.slvs")
               if "out" not in p.parts and not slvs.has_raw_magic(p.read_bytes())]
        self.assertEqual(bad, [], "sources with a UTF-8-mangled header")

    def test_fix_repairs_utf8_mangled_header(self):
        # Reproduce the corruption an editor causes: decode as latin-1, re-encode as UTF-8.
        data = REAL.read_bytes()
        mangled = self.tmp / "m.slvs"
        mangled.write_bytes(data.decode("latin-1").encode("utf-8"))
        self.assertTrue(slvs.has_utf8_magic(mangled.read_bytes()))
        self.assertFalse(slvs.has_raw_magic(mangled.read_bytes()))
        self.assertTrue(slvs.fix_magic(mangled))
        self.assertEqual(mangled.read_bytes(), data)
        self.assertFalse(slvs.fix_magic(mangled), "second fix must be a no-op")

    def test_fix_normalises_crlf(self):
        crlf = self.tmp / "c.slvs"
        crlf.write_bytes(REAL.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(slvs.fix_magic(crlf))
        self.assertEqual(crlf.read_bytes(), REAL.read_bytes())

    def test_parse_refuses_mangled_file(self):
        mangled = self.tmp / "m.slvs"
        mangled.write_bytes(REAL.read_bytes().decode("latin-1").encode("utf-8"))
        with self.assertRaises(ValueError):
            slvs.parse(mangled)


class ParseTests(unittest.TestCase):
    def test_records_and_kinds(self):
        recs = slvs.parse(REAL)
        kinds = [r["_kind"] for r in recs]
        self.assertEqual(kinds.count("AddGroup"), 2)
        self.assertEqual(kinds.count("AddRequest"), 6)
        self.assertEqual(kinds.count("AddConstraint"), 9)
        self.assertNotIn("AddEntity", kinds, "hand-written sources carry no entities")

    def test_params_are_initial_guesses(self):
        p = slvs.params(REAL)
        self.assertEqual(p["00050014"], 10.0)     # apex v guess, not the solved 75

    def test_remap_block_is_captured(self):
        recs = slvs.parse(ROOT / "mwe" / "04_bolt_pattern" / "flange.slvs")
        rot = [r for r in recs if r.get("Group.type") == "5200"][0]
        self.assertEqual(rot["Group.remap"], [], "source leaves the remap empty; regenerate fills it")

    def test_constraint_lookup(self):
        c = slvs.constraints(REAL)
        self.assertEqual(c["00000009"]["Constraint.type"], "120")
        self.assertEqual(c["00000009"]["Constraint.reference"], "1")


if __name__ == "__main__":
    unittest.main()
