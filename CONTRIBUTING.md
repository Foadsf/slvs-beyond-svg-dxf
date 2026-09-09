# Contributing

Contributions are welcome under the same licence as the repository
(CC BY-SA 4.0, see `LICENSE`).  By submitting a change you agree to that.

## Ground rules for a new MWE

1. **One idea per MWE.**  Each folder shows one thing SVG/DXF cannot express.
   If it needs two paragraphs to explain, split it.
2. **Hand-written source, machine-verified.**  The `.slvs` files in an MWE
   folder are the deliverable and must stay minimal: groups, params (initial
   guesses only), requests, constraints.  No `Entity` records: SolveSpace
   regenerates them.  No `Group.remap` contents: regenerate fills them
   deterministically (`src/group.cpp`, `Group::Remap`).
3. **A variant that changes one thing.**  Ship a second file that differs
   from the first by one (or two closely related) lines and prove the
   geometry followed.  Say what changed in the README with a `diff`.
4. **Every claim gets a check.**  Add `mwe/NN_name/check.py` defining
   `run(ctx)` (see any existing one) that reads the *regenerated* file in
   `out/` and compares solved values with values derived from the
   constraints.  Include a negative control: assert the solved value
   differs from the initial guess in the source.
   For GD&T examples: cite the Cogorno chapter, put feature control frames
   in COMMENT text, state pass/fail from the numbers in the README, and
   keep outlines closed so `thumbnail` draws no warning.
5. **Source facts, not memory.**  A type number, field name or behaviour is
   cited to a file and line in the SolveSpace source (`src/sketch.h`,
   `src/file.cpp`, `src/group.cpp`, ...) or to a measurement with the CLI.
   The transcript that seeded this repository contained fluent, wrong
   descriptions of this format; `docs/provenance.md` lists them.

## Editing `.slvs` files safely

The first line starts with the raw bytes `B1 B2 B3`.  Most editors decode a
file as UTF-8 and re-encode on save, which silently turns those three bytes
into six and makes SolveSpace report *"Unrecognized data in file"*.

- `.editorconfig` asks editors to use latin-1 for `*.slvs`.
- After any edit, run `python tools/slvs.py check mwe/**/*.slvs`; if a file
  is flagged, `python tools/slvs.py fix FILE` repairs the header and CRLFs.
- `tests/test_slvs_tools.py` fails if any shipped source has a mangled header.

## Workflow

```
python tools/build.py --cli /path/to/solvespace-cli   # regenerate + export into mwe/*/out/
python tools/check.py                                 # geometry assertions
python -m unittest discover -s tests                  # offline tool tests
```

Commit the SVG and PNG renders in `out/` (the READMEs embed them); DXF, STEP,
STL and regenerated `.slvs` are ignored by `.gitignore`.

## Tested with

SolveSpace CLI `3.2~8f4b12ca` (master, 2026-09), Windows x86 build.  The
format has been stable since the 3.0 series; if a newer version changes
behaviour, record the version and the difference in the README.
