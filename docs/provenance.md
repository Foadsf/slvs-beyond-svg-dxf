# Provenance, and a fact-check of the seed

This repository grew out of a conversation with a large language model
(Google Gemini, September 2026) about the state of FLOSS 2D CAD.  Its
opening diagnosis was right and is worth keeping:

> DXF and SVG are static rendering containers, not semantic models.  They
> serialize flat, evaluated primitives while discarding the constraint
> graph, variable tables and associative reference links.

It then presented SolveSpace's `.slvs` as "The Variational Text Standard"
and, asked for an MWE, produced file excerpts, CLI invocations and Python
code that were fluent, specific, and mostly invented.  The *capabilities*
it attributed to `.slvs` are real, and this repository demonstrates them.
The *details* it gave would have sent a reader down several dead ends, so
they are recorded here with what the SolveSpace source actually says.

Legend: **verified** = checked against the source tree at master `8f4b12ca`
or by running `solvespace-cli 3.2~8f4b12ca`; **unverified** = not checked
here and not relied upon.

## Claims about the file format

| Claim in the transcript | Status | What is actually the case |
|---|---|---|
| `Param.00000001.val = 0.000000` (numbered keys) | wrong, verified | Keys are unnumbered: `Param.h.v.=00040010` then `Param.val=…`, committed by a bare `AddParam` line (`src/file.cpp`, `SAVED[]`, `LoadFromFile`). |
| `Entity.00000010.type = 100 # POINT_IN_2D` | wrong, verified | `POINT_IN_2D` is `2001`; `100` is the *Request* type WORKPLANE (`src/sketch.h`). Entities are ignored on load and regenerated from requests; a file that carried only entities would draw nothing. |
| `Entity.00000020.type = 200 # LINE_SEGMENT` | wrong, verified | `200` is the *request* type; the entity type is `11000`. |
| `Constraint…type = 14 # HORIZONTAL`, `= 2 # PT_PT_DISTANCE`, `= 1 # COINCIDENT` | wrong, verified | `80`, `30`, `20` respectively (`src/sketch.h`). |
| `Group.00000001.type = 1` for a sketch | wrong, verified | A sketch in a workplane is `5001`; the references group is `5000`. |
| `Group.00000002.type = 4 # GROUP_LINKED`, `Group.meshFile = "skeleton.slvs"` | wrong, verified | LINKED is `5300`; the fields are `Group.impFile` and `Group.impFileRel` (see MWE 05). |
| Constraints written as `Constraint.PT_PT_DISTANCE` etc. "with explicit numerical values or variable expressions" | half right | Types are numeric. Values are literal numbers; the format has **no variables or expressions**. The GUI evaluates an expression you type and stores the result. |
| Points "declared with unique numeric IDs" that constraints reference | right | Handles, 8 hex digits, structured as request/entity/param (primer §3). |
| A linked master "re-executes the solver graph" downstream when it changes | right in effect, wrong in mechanism | The downstream reads the master's *solved entities* from disk (`ReloadAllLinked`), so the master must be regenerated first; then the downstream's own constraints re-solve against the new positions (MWE 05). |

## Claims about the CLI and export

| Claim | Status | Actual |
|---|---|---|
| `solvespace-cli -o part.step part.slvs`, `-o drawing.dxf --view top`, `-o mesh.stl --chord-tol` | wrong shape, verified | `solvespace-cli export-surfaces --output %.step part.slvs`; `export-view --view top --output %.dxf`; `export-mesh --chord-tol 0.05 --output %.stl` (`src/platform/entrycli.cpp`). |
| `solvespace-cli export model.slvs -o output.step`, `thumbnail model.slvs -o thumb.png` | wrong, verified | There is no `export` verb; `thumbnail` needs `--view` and `--size`. |
| "Headless CLI export exists as PR branches implementing `--export`"; "community headless builds" | wrong, verified | `solvespace-cli` has been in upstream master since before 3.0 and is built by every release CI job. |
| `xvfb-run … solvespace --export output.step input.slvs` | wrong, verified | The GUI has no `--export`; a trailing argument is a file to open (`src/platform/entrygui.cpp`). |
| Exports to IGES | wrong, verified | `grep -ri iges src/` finds nothing. |
| STEP "AP214 or AP203" | half right, verified | The export declares `FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'))`, i.e. AP203. |
| STEP exports "true mathematical surfaces (planes, cylinders, …)" | half right, verified | Everything is written as `B_SPLINE_SURFACE_WITH_KNOTS`; planes and cylinders are exact as B-splines but are not `PLANE` / `CYLINDRICAL_SURFACE` entities (MWE 06). |
| Writes true arcs to DXF and SVG rather than polylines | right, verified | MWE 02's DXF has `ARC` entities; its SVG outline uses `A` arc commands. |
| "Export 2D Section" for laser-cut profiles | right for the GUI | Not available from the CLI, whose 2D verbs are `export-view` and `export-wireframe`. |
| Mesh density set in the GUI configuration | right | On the CLI it is `--chord-tol`, in mm for exports. |

## Claims about installation on Windows

| Claim | Status | Actual |
|---|---|---|
| "The official distribution bundles solvespace.exe and solvespace-cli.exe together starting from 3.1" | wrong, verified | No Windows release has shipped the CLI. Release CI builds it and discards it (`.github/scripts/build-windows.sh` renames only `solvespace.exe`). Upstream issue [#1770](https://github.com/solvespace/solvespace/issues/1770), PR [#1771](https://github.com/solvespace/solvespace/pull/1771); the maintainer called the omission intentional and suggested shipping it zipped. |
| Later in the same conversation: "official releases do not ship solvespace-cli.exe" | right | The conversation contradicted itself; the second statement is the true one. |
| "The Windows release is a single, self-contained 32-bit GUI executable" | wrong, verified | v3.2 ships four: `solvespace_x86.exe`, `solvespace_x64.exe` and OpenMP variants. |
| `scoop shim add solvespace-cli …` will expose the CLI | wrong | There is nothing to shim; the package contains no CLI. |
| FreeCAD can open `.slvs` via `import solvespace; solvespace.open(...)` | wrong, verified | GitHub code search over `FreeCAD/FreeCAD` for `solvespace` and `slvs`: zero hits. |
| `pip install python-solvespace` gives headless STEP/DXF/SVG export | wrong | Solver bindings only: no file I/O, no export (primer §9). |
| The Python API shown (`slvs.System()`, `create_group()`, `add_constraint(g, slvs.C_COINCIDENT, …)`, `c_hyp.val = 200`) | unverified | Not checked here. Do not copy it without reading the package's own documentation. |
| "Levenberg-Marquardt/BFGS non-linear solver" | unverified | SolveSpace's solver is a Newton-type iteration with a rank-revealing linear solve (`src/system.cpp`); the exact algorithm was not checked for this repository and is irrelevant to the file format. |

## How this repository avoids the same failure

Every type number, field name and behaviour claimed in `README.md`,
`docs/slvs-primer.md` and the MWE READMEs is cited to a SolveSpace source
file, or was measured by running the CLI on the files in this repository,
and `tools/check.py` re-measures the geometry claims on every build.
If you find a statement here that is not backed that way, open an issue:
it is a bug.
