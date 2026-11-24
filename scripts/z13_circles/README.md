# Z13 circles image analysis

Code for `results/z13_circles/` (write-up in `results/FINDINGS.md`, 2026-11-24). Images are not in the repo:
see `results/z13_circles/IMAGES.md` for how to fetch them; the run scripts take their paths as arguments.

| File | Role |
|---|---|
| `measure.py` | Pre-registered shape distance and likelihood ratio (sealed, fork commit 1f041bc) |
| `metrics.py` | Pre-registered tournament metrics M1-M7 (sealed, fork commit 0591b39) |
| `SEALED.sha256` | sha256 of the two sealed files; `tests/test_z13_circles.py` and every run script check it |
| `segment.py` | Finds the 13 cipher-line glyph boxes from ink gaps |
| `grid_seg.py` | Cuts the Z408/Z340 grids into cells (I1b, I1c) |
| `run_i1b.py` | Look-alike power check |
| `run_i1c.py` | Metric tournament (`bench`) and its single application to the circles (`circles`) |
| `robustness.py` | Exploratory robustness checks |
| `common.py` | Paths, hash check, page arguments |
| `glyph_widths.py` | Glyph widths on one line of a scan (compares image resolution; see `IMAGES.md`) |

Do not edit `measure.py` or `metrics.py`: their hashes are part of the pre-registration. Note that `metrics.py`
(byte-identical to the sealed file) inserts an absolute path from the original workspace at the front of
`sys.path` before `import measure`; on any other machine that directory does not exist and Python falls back to
`measure.py` next to it, which is what the run scripts and tests rely on (they import `measure` first).
