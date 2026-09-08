# slvs-beyond-svg-dxf

Six minimal working examples of things a SolveSpace `.slvs` file can say
that an SVG or a DXF cannot: relationships instead of coordinates.

SVG and DXF are *evaluated* drawings.  They store where every vertex ended
up, and nothing about why.  A `.slvs` file stores the *problem*: which
points must coincide, which lines are tangent, which distance is 100, and it
stores only rough initial guesses for the coordinates.  SolveSpace's
non-linear constraint solver produces the geometry on load.  Change one
number in the text and the whole drawing re-solves, and the same file can be
exported to SVG, DXF, PDF, STEP and STL from the command line.

Every example is a hand-written `.slvs` file small enough to read in full,
a second file that differs from it by one line, the exports SolveSpace
produced from both, and an automated check that the solved geometry is what
the constraints imply.

## The examples

| | Shows | One-line change | Verified result |
|---|---|---|---|
| [01 Variational triangle](mwe/01_variational_triangle/) | coordinates solved from constraints; a *reference* dimension that reports the measured angle | hypotenuse 125 → 200 | apex (100, 75) → (100, 173.2); 36.87° → 60° written back into the file |
| [02 Tangent slot](mwe/02_tangent_slot/) | tangency, equal radius, construction geometry that drives but does not export | pitch 60 → 90 | four tangent points exactly on their circles; edges horizontal without being told so |
| [03 Symmetric bracket](mwe/03_symmetric_bracket/) | symmetry as a constraint, not a copy; point-on-line | top width 40 → 70 | both top corners move by 15, opposite ways; measured side length rewritten |
| [04 Bolt pattern](mwe/04_bolt_pattern/) | step-and-repeat whose count and pitch angle are model parameters | 6 holes → 8 holes | copies at exact multiples of 45°, all on the pitch circle |
| [05 Transclusion](mwe/05_transclusion/) | a *linked* master file; downstream geometry constrained to it | master pitch 80 → 100, **downstream file byte-identical** | holes move from ±40 to ±50 |
| [06 Sketch to solid](mwe/06_sketch_to_solid/) | the drawing is also a 3D part: STEP B-rep and STL from the same source | thickness 8 → 20 | STL bounding box 100 × 60 × 8 → × 20; STEP with 10 surfaces |

<p align="center">
<img src="mwe/01_variational_triangle/out/triangle.hyp200.png" width="30%">
<img src="mwe/04_bolt_pattern/out/flange.8holes.png" width="30%">
<img src="mwe/06_sketch_to_solid/out/plate.depth20.iso.png" width="30%">
</p>

## Capability matrix

| Capability | SVG | DXF | `.slvs` | MWE |
|---|---|---|---|---|
| Coordinates computed from relationships | – | – | ✓ non-linear solver | 01 |
| Driving dimension (edit a number, geometry follows) | – | – | ✓ `Constraint.valA` | all |
| Driven / reference dimension (measured, written back) | – | text override only | ✓ `Constraint.reference=1` | 01, 03 |
| Tangency, perpendicularity, equal radius, symmetry, midpoint, point-on-curve | – | – | ✓ ~40 constraint types | 02, 03 |
| Construction geometry (drives, does not export) | – | layer convention | ✓ `Request.construction=1` | 02, 03, 04 |
| Pattern with parametric count and pitch | `<use>` copies | `INSERT` copies | ✓ ROTATE / TRANSLATE groups, copies still constrainable | 04 |
| External reference that local geometry can constrain to | `<use href>` displays only | `XREF` displays only | ✓ LINKED group + constraints to linked entities | 05 |
| Same source drives 2D drawing and 3D solid | – | – | ✓ EXTRUDE / LATHE / REVOLVE groups; STEP, STL | 06 |
| Dimensions exported as real dimension entities | – | ✓ as input | ✓ writes DXF `DIMENSION` | 01 |
| Exact arcs preserved on export | arc commands | `ARC` | ✓ exports both | 02 |
| Human-readable, line-diffable text | ✓ | ✓ | ✓ | all |

What `.slvs` does **not** give you, so you are not oversold: there are no
named variables or expressions in the file (a dimension is a literal number;
relations between dimensions are constraints such as `EQUAL_LENGTH_LINES`,
`LENGTH_RATIO`, `LENGTH_DIFFERENCE`); no units (millimetres are implied); no
layers beyond styles; text only as TTF outlines; and the solver is numeric,
so results carry ~1e-8 relative error rather than being exact.

## Quick start

You need `solvespace-cli`, the headless SolveSpace binary, and Python 3.9+
(standard library only).

```
python tools/build.py --cli /path/to/solvespace-cli    # regenerate + export into mwe/*/out/
python tools/check.py                                  # assert the solved geometry
python -m unittest discover -s tests                   # offline tests of the tools
```

`build.py` also honours `$SOLVESPACE_CLI` and `PATH`.  Use `--only 05` to
build one example, `-v` to see every CLI call.

### Getting `solvespace-cli`

- **Linux:** distribution packages of SolveSpace include it (`solvespace-cli`
  on Debian/Ubuntu/Fedora/Arch); the Flatpak exposes it as
  `flatpak run --command=solvespace-cli com.solvespace.SolveSpace`.
- **macOS:** inside the app bundle, `SolveSpace.app/Contents/MacOS/solvespace-cli`.
- **Windows:** the official release does **not** ship it (the CI builds it and
  discards it; see upstream issue
  [#1770](https://github.com/solvespace/solvespace/issues/1770) and PR
  [#1771](https://github.com/solvespace/solvespace/pull/1771)).  Build from
  source with CMake + MSVC, or download the `solvespace-cli.exe` artifact of a
  CI run.  WinGet, Scoop and Chocolatey deliver the GUI only.
- **Any platform:** `git clone --recursive https://github.com/solvespace/solvespace`,
  then `cmake -B build && cmake --build build`; the CLI is `build/bin/solvespace-cli`.

The GUI binary has no export flags on any platform; a trailing argument is
a file to open.

## Reading a `.slvs` file

A ten-minute primer is in [`docs/slvs-primer.md`](docs/slvs-primer.md): the
magic bytes, the record grammar, how handles encode request → entity →
parameter, why the sources here contain no `Entity` records, and how
derived entities (pattern copies, linked entities, extruded copies) get
their handles from `Group.remap`.

Three traps that cost time, recorded so you do not pay for them again:

1. The file starts with **raw bytes `B1 B2 B3`**, not UTF-8.  An editor that
   re-saves as UTF-8 breaks the file.  `python tools/slvs.py check` detects
   it and `fix` repairs it.
2. The CLI's `--output` pattern must be a bare `%.svg`.  `%` expands to the
   input path *including its directory*, so `out/%.svg` writes to
   `out/out/name.svg` and fails, while still printing `Written '…'` and
   exiting 0.
3. A linked file is read at the **entity** level, so after editing a master
   you must `regenerate` the master before anything that links it.

## Layout

```
mwe/NN_name/           one example: hand-written .slvs source(s), a one-line variant,
  README.md            what it shows, the file explained, the diff, verified numbers
  build.json           regenerate order, view, exports
  out/                 what solvespace-cli produced (svg/png committed; dxf/step/stl/slvs regenerated)
tools/slvs.py          byte-safe .slvs reader; magic-byte checker/fixer
tools/build.py         runs the CLI for every example
tools/check.py         geometry assertions, with negative controls
tests/                 offline unit tests for the tools
docs/slvs-primer.md    the format, cited to SolveSpace source lines
docs/provenance.md     where this came from, and which claims of the seed were wrong
```

## Provenance

This repository started as a fact-check.  An LLM conversation described
`.slvs` as "The Variational Text Standard" and gave a fluent, plausible and
largely fabricated description of the format, the CLI, and the Python
bindings.  The capabilities it claimed are real; the details it invented are
listed with corrections in [`docs/provenance.md`](docs/provenance.md).  Every
statement in this repository about the format is cited to a file and line
in the SolveSpace source or measured with the CLI (version `3.2~8f4b12ca`,
master as of 2026-09).

## Licence

[CC BY-SA 4.0](LICENSE).  Copyright © 2026 Foad S. Farimani and
contributors.  Initial version drafted with Claude (Anthropic) and verified
against SolveSpace by running the binary; SolveSpace itself is GPLv3 and is
not included here.
