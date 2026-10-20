# R029 source-supported reference geometry v3

**R029 DONE,2026-10-20:** all48 test laps pass the frozen v3 gates; native audit,
portable scientific replay,544 regression tests and Python3.11/3.12 CI pass.
See the [final report](../verification/track-reconstruction-v3-report.md).
This is a reconstructed
reference RACING TRACE for Bahrain and Monza, not a surveyed centerline or road
boundary. The [protocol](../../research/protocols/TRACK_RECONSTRUCTION_V3.md),
[source-coherence equations](../../research/equations/SOURCE_COHERENT_CURVATURE_V3.md),
[observed-support equations](../../research/equations/OBSERVED_TRACK_SUPPORT_V2.md)
and [boundary/pose equations](../../research/equations/OBSERVED_TRACK_BOUNDARIES_V2_1.md)
define the exact method and acceptance scope.

The four verified non-benchmark race archives retain their original source/mask
seals. Native XY converts decimetres to metres. Ten2024 training laps per circuit
fit shape; ten2024 laps from the other driver select among six candidates.
The2023 tests contain24 retrospective laps plus24 additional confirmation laps,
with no substitution. All88 selected laps and every native test position remain
inspectable. Nine reserved whole-event benchmarks remain protected. These are
previously used development events; additional laps are not untouched benchmarks.

All native intervals>.75s stay unsupported. Training/validation require two
supported timing anchors and raw closure<=30m. Test-only unsupported anchors are
UNKNOWN and omitted, with>=98% observed time coverage; no extrapolation or long-gap
fill. Source reversals invalidate forward curvature stencils without removing
positions from XY scores. Unfiltered chronological proxy values remain saved as
diagnostics. Every10m model station requires three training donors; ten
leave-one-lap fits quantify descriptive sensitivity, not calibrated confidence.

Shape uses periodic Fourier ridge coefficients, analytic derivatives and monotone
integrated arc distance. Eight proper rigid pose-refinement steps compare held-out
positions against the frozen curve. Errors are CONDITIONAL REGISTERED-SHAPE
errors after optimizing rigid pose. Public provider reconstruction, registration
and proxy targets prevent interpreting small residuals as physical survey accuracy.
Physical width, validated elevation, surveyed centerline, official DRS zones and
full pit route remain UNKNOWN. Research ancillary requests raise errors.

The command name retains backward compatibility; the two explicit flags select
the declared v3 scientific profile. Use fresh outputs from the checkout:

```powershell
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-v2 --observed-boundaries --coherent-curvature --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --mask-2024 .cache/tyre-dataset-20261011.json --mask-2023 .cache/r026-proxy-public-20261013/eligible_input.json --output .cache/track-reference-v3-new
.venv/Scripts/python.exe -m apexsim.cli verify-track-reconstruction-v2 .cache/track-reference-v3-new
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-v2-smoke --observed-boundaries --coherent-curvature --output .cache/track-reference-v3-smoke-new
.venv/Scripts/python.exe research/scripts/plot_reference_geometry.py --input .cache/track-reference-v3-new --output .cache/track-reference-v3-figures-new
```

Independent native-table/NumPy audit of a completed run:

```powershell
.venv/Scripts/python.exe research/scripts/audit_reference_geometry.py --input .cache/track-reference-v3-new --development .cache/r029-v2-development-20261019 --retrospective .cache/r029-v2-1-research-20261019 --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --output .cache/track-reference-v3-audit-new.json
```

Artifacts retain raw XY/times/native parents and source-labelled metadata, every
projected position, candidate scores, fixed coefficients/arc tables, time/derivative
masks, raw and accepted curvature proxies, per-lap and stratum identity, donor
matrices, sensitivity and unknown-aware annotations. The manifest is written last.
Portable verification refits saved training inputs and reproduces every array and
decision without original caches. Annotation station projections replay; original
native-bracket reconstruction requires verified source archives. Hashes establish
local consistency, not provider authentication. Bulk arrays stay ignored locally.

V1, strict v2 and v2.1 failures remain preserved. Acceptance of v3 reference
geometry does not promote the production simulator or establish calibrated vehicle
dynamics, complete closed-loop real laps, a validated world model or R3 maturity.
