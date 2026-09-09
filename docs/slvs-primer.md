# The `.slvs` format in ten minutes

Everything below is read from the SolveSpace source tree (`src/file.cpp`,
`src/sketch.h`, `src/request.cpp`, `src/group.cpp`) at master `8f4b12ca`
(2026-09) or measured by running `solvespace-cli`.  Where the source
disagrees with something you read elsewhere, the source wins.

## 1. Header

The first line is three raw bytes followed by a version string:

```
B1 B2 B3 "SolveSpaceREVa" 0A
```

`B1 B2 B3` are not UTF-8.  Open the file in binary mode or as latin-1.
The loader (`SolveSpaceUI::LoadFromFile`) compares the line to
`VERSION_STRING`; anything else without an `=` sets `fileLoadError`.

## 2. Records

The rest is `Key=Value` lines.  A bare marker line commits the record:
`AddGroup`, `AddParam`, `AddRequest`, `AddEntity`, `AddConstraint`,
`AddStyle`.  Keys are listed in the `SAVED[]` table in `src/file.cpp`.
Fields at their default are omitted when saving.  Handles are 8 hex digits.
Floats are written with 20 decimals; any decimal parses.

One quirk: the parameter handle key has a trailing dot, `Param.h.v.=`.
That is the table's spelling, not a typo.

What the loader does with each kind (`file.cpp`, `LoadFromFile`):

| Record | On load |
|---|---|
| `Group` | kept |
| `Param` | kept **as the initial guess** for the solver ("params are regenerated, but we want to preload the values") |
| `Request` | kept: this is the user's geometry |
| `Entity` | **ignored** ("entities are regenerated") except when the file is being *linked* |
| `Constraint` | kept |
| `Style` | kept |
| `Triangle`, `Surface`, `Curve`, … | ignored: cached mesh/shell, regenerated |

So a hand-written file needs groups, params, requests and constraints.
The sources in this repository contain nothing else.  `regenerate`
writes everything back, entities included, with `Entity.actPoint.{x,y,z}`
holding the solved positions.

## 3. Handles

```
Request  r            h.v = r                     e.g. 00000004
Entity   of request r h.v = (r << 16) | i         e.g. 00040000 (the line), 00040001, 00040002 (its points)
Param    of request r h.v = (r << 16) | i         e.g. 00040010
Entity   of group g   h.v = 0x80000000 | (g << 16) | i    e.g. 80020000 (group 2's workplane)
Param    of group g   h.v = 0x80000000 | (g << 16) | i    e.g. 80030002
```

(`src/sketch.h`, `hRequest::entity`, `hRequest::param`, `hGroup::entity`,
`hGroup::param`.)

`Request::Generate` (`src/request.cpp`) fixes the entity and parameter
indices for each request type:

| Index | Meaning |
|---|---|
| entity `0` | the request's own entity (line, arc, circle, …); datum points use index 0 for the point |
| entity `1 … n` | its points, in order |
| entity `32` (0x20) | its normal, if it has one (workplane, circle, arc, text) |
| entity `64` (0x40) | its distance (circle radius) |
| param `16 + 3i + {0,1,2}` | point *i*'s u,v (2D) or x,y,z (3D) |
| param `32 … 35` | normal quaternion (3D only) |
| param `64` | radius |

Example: request `00000005` is an arc; `00050000` is the arc, `00050001`
its centre, `00050002` its start, `00050003` its end, and the centre's
coordinates are params `00050010` and `00050011`.

## 4. Type numbers (`src/sketch.h`)

**Group.type:** `5000` DRAWING_3D · `5001` DRAWING_WORKPLANE · `5100` EXTRUDE ·
`5101` LATHE · `5102` REVOLVE · `5103` HELIX · `5200` ROTATE · `5201` TRANSLATE ·
`5300` LINKED.

**Group.subtype:** `6000` WORKPLANE_BY_POINT_ORTHO · `6001` WORKPLANE_BY_LINE_SEGMENTS ·
`6002` WORKPLANE_BY_POINT_NORMAL · `7000` ONE_SIDED · `7001` TWO_SIDED · `7004` ONE_SKEWED.

**Request.type:** `100` WORKPLANE · `101` DATUM_POINT · `200` LINE_SEGMENT ·
`300` CUBIC · `301` CUBIC_PERIODIC · `400` CIRCLE · `500` ARC_OF_CIRCLE · `600` TTF_TEXT · `700` IMAGE.

**Entity.type** (what `regenerate` writes): points `2000` POINT_IN_3D, `2001` POINT_IN_2D,
`2010`–`2014` derived points (N_TRANS, N_ROT_TRANS, N_COPY, N_ROT_AA, N_ROT_AXIS_TRANS);
normals `3000`–`3012`; `4000` DISTANCE; `10000` WORKPLANE; `11000` LINE_SEGMENT;
`12000` CUBIC; `13000` CIRCLE; `14000` ARC_OF_CIRCLE; `15000` TTF_TEXT.

**Constraint.type**, the ones used here: `20` POINTS_COINCIDENT · `30` PT_PT_DISTANCE ·
`32` PT_LINE_DISTANCE · `42` PT_ON_LINE · `61` SYMMETRIC_HORIZ · `62` SYMMETRIC_VERT ·
`63` SYMMETRIC_LINE · `80` HORIZONTAL · `81` VERTICAL · `90` DIAMETER · `100` PT_ON_CIRCLE ·
`110` SAME_ORIENTATION · `120` ANGLE · `122` PERPENDICULAR · `123` ARC_LINE_TANGENT ·
`130` EQUAL_RADIUS.  Others: `31` PT_PLANE_DISTANCE, `41` PT_IN_PLANE, `50` EQUAL_LENGTH_LINES,
`51` LENGTH_RATIO, `54` EQUAL_ANGLE, `56` LENGTH_DIFFERENCE, `60` SYMMETRIC, `70` AT_MIDPOINT,
`121` PARALLEL, `124` CUBIC_LINE_TANGENT, `125` CURVE_CURVE_TANGENT, `200` WHERE_DRAGGED,
`1000` COMMENT.

Constraint behaviours worth knowing (all `src/constrainteq.cpp`):

- `200` WHERE_DRAGGED pins `ptA` to the numeric value its params hold
  when equations are generated, i.e. to the `Param` records in the file.
  It is the natural way to store *measured* coordinates.
- `56` LENGTH_DIFFERENCE and `51` LENGTH_RATIO take two **lines**
  (`entityA`, `entityB`) and set |A| − |B| = `valA` or |A| / |B| = `valA`.
  With `reference=1` the difference is measured and written back.
- `52` EQ_LEN_PT_LINE_D: |`entityA`| equals the distance from `ptA` to
  line `entityB`, squared, so the side is chosen by the initial guess.
- `32` PT_LINE_DISTANCE in a workplane is signed.
- `120` ANGLE uses a cosine; its derivative vanishes at 0° and 180°, so
  use `121` PARALLEL / `122` PERPENDICULAR there.  `other=1` flips one
  direction.
- `70` AT_MIDPOINT with a point and a line is two equations in 2D.
- `1000` COMMENT draws `Constraint.comment` centred at `disp.offset`
  (plus `ptA` if given).  Exports: DXF `TEXT` with the Unicode intact;
  SVG/PNG through the built-in vector font, which lacks the GD&T symbols
  (measured 2026-09: ∠ ∥ ° Ø render, ⌖ ⟂ Ⓜ ◎ ⌓ ↗ do not).

## 5. The mandatory skeleton of any file

Group `00000001` `#references` (type 5000) with requests 1, 2, 3 (the XY,
YZ, ZX reference workplanes; their orientation is forced by
`ForceReferences()` in `src/generate.cpp`, so their params can be
omitted).  The origin point is entity `00010001`; the XY normal is
`00010020`.

A 2D sketch is a group of type 5001 whose own workplane entity is
`800N0000` (with normal `800N0001` and origin `800N0002`).  Requests in it
carry `Request.workplane.v=800N0000`; constraints carry
`Constraint.workplane.v=800N0000`.  A constraint with no workplane is in 3D.

## 6. Derived entities and `Group.remap`

Extrude, lathe, rotate, translate and link groups *copy* entities from
their source.  Each copy gets a handle from the group's remap table:

```
Group.remap={
    5 00040001 1001
}
```

means "(entity 00040001, copy tag 1001) → index 5", so the copy is
`0x80000000 | 3<<16 | 5 = 80030005` for group 3.  Tags: copy number for
patterns (`1000` REMAP_LAST), `1001` REMAP_TOP / `1002` REMAP_BOTTOM for
extrusions, `0` for links.  `Group::Remap` (`src/group.cpp`) appends
missing entries in the order they are first requested, so a source file may
leave the table empty; regenerate fills it identically every time.

To constrain to a derived entity (the depth of an extrusion, the angle of a
pattern, a point in a linked file), regenerate once, read the index from
the table, and write the constraint against that handle.

## 7. Links

A LINKED group (5300) carries `Group.impFile` (absolute, informational)
and `Group.impFileRel` (relative to the linking file; the one used).
`ReloadAllLinked` reads the linked file's `Entity` records, so a master
must be saved/regenerated before dependants see a change.  The link has
seven free parameters (translation + quaternion); constrain them
(POINTS_COINCIDENT to the origin, SAME_ORIENTATION to a normal) or the
solver may move the linked part instead of your geometry.

## 8. The CLI

```
solvespace-cli regenerate        [--chord-tol t]                    file.slvs   (re-saves in place)
solvespace-cli export-view       --view V --output PAT [--bg-color on|off] file.slvs   → svg pdf eps dxf step plt ngc
solvespace-cli export-wireframe  --output PAT                       file.slvs   → step dxf
solvespace-cli export-mesh       --output PAT [--chord-tol t]       file.slvs   → stl obj html js wrl
solvespace-cli export-surfaces   --output PAT                       file.slvs   → step
solvespace-cli thumbnail         --view V --size WxH --output PAT   file.slvs   → png
```

`V` ∈ top bottom left right front back isometric.  For an XY sketch,
`front` maps u→x, v→y.  `PAT` must be `%.ext` (see README, trap 2).  The CLI
prints `Written '…'.` even after `Error: Couldn't write …` and exits 0;
stat the output.

Not in the CLI: the GUI's *Export 2D Section*, and there is no IGES
anywhere in SolveSpace.

## 9. Python

Upstream ships a Cython wrapper of the solver (`src/slvs/lib.pyx`,
published as `slvs`); `python-solvespace` on PyPI is a third-party wrapper
of the same library.  Both build and solve constraint systems in memory.
Neither reads or writes `.slvs`, and neither exports.  For files, shell out
to `solvespace-cli` as `tools/build.py` does.
