# R029 reference geometry model/data card

This is a two-dimensional reconstructed reference RACING TRACE in the research
namespace. It is neither a surveyed road centerline nor calibrated track
boundaries. See the [frozen protocol](../../research/protocols/TRACK_RECONSTRUCTION.md),
[equations](../../research/equations/REFERENCE_GEOMETRY_V1.md) and
[verification report](../verification/track-reconstruction-report.md).

**Current public result: INCONCLUSIVE.** The frozen source gate rejects14/24
selected laps (33 intervals above 0.75s; largest1.32s). No real curve was fitted
and no public shape/curvature accuracy or task closure is claimed. The numerical
geometry path passes analytic and synthetic controls. The native-source audit
persists both accepted and rejected evidence and replays without source caches.

The frozen cohort uses verified Bahrain/Monza 2024 race archives for training/
validation and separate2023 races for final DEVELOPMENT tests. Per circuit:
three earliest eligible driver 4 training laps, three driver 44 validation laps,
and three2023 test laps per driver. Eligibility is the original source-bound
clean-dry R021/R026 mask. No fastest-lap or outcome-driven replacement occurs.
The permanent benchmark weekends remain excluded.

Native source position units convert decimetres to metres. Only supported native
pos/OnTrack rows enter complete lap traces, with bounded interpolation of the
two timing anchors. Gaps, timing inconsistencies, degenerate samples and excessive
raw endpoint closure fail explicitly. No canonical telemetry table is imputed.

Training-only periodic Fourier coefficients produce analytic heading/curvature
and monotone arc distance. Validation chooses one frozen smoothing candidate.
Full-lap rigid registration removes source pose differences before comparison;
test shape is never fitted, rescaled or warped. Results concern registered shape,
not absolute geographic accuracy or online localization.

The raw training polyline remains a positional baseline. Coarse held-out
turning-angle curvature is explicitly a PROXY. Training-lap sensitivity ranges
are not calibrated population confidence. Both pre-fit raw closure and structural
curve closure remain visible, alongside all per-lap residuals and gate failures.

The `GeometryProvider` contract exposes station/XY/heading/curvature for both
legacy synthetic and research curves. Existing production sampling is unchanged.
Research width, validated elevation, official DRS zones, surveyed centerline and
complete pit route remain UNKNOWN. Unsupported ancillary requests raise errors;
the legacy12m/zero/false defaults are not used by this reconstruction workflow.
Source sector and pit timing projections are labelled with support and spread.

Run the pre-fit source audit from the checkout with fresh outputs:

```powershell
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-source-audit --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --mask-2024 .cache/tyre-dataset-20261011.json --mask-2023 .cache/r026-proxy-public-20261013/eligible_input.json --output .cache/track-source-audit-new
.venv/Scripts/python.exe -m apexsim.cli verify-track-reconstruction-source-audit .cache/track-source-audit-new
```

The frozen cohort returns `REJECT_FROZEN_SOURCE_SUPPORT`,10 supported of 24 laps,
`fit_performed=false` and `task_closure_eligible=false`. The audit includes native
position snapshots, original selected lap timing rows, all per-lap decisions,
source manifests and a manifest written last. Replaying the snapshots establishes
local consistency, not provider authentication. No geometry is fit during an
audit, including a source audit whose support checks all pass.

The geometry command below fails at the first unsupported selected lap for this
cohort. It must not be treated as an accepted public example. The scientific
verifier applies only when a complete geometry artifact exists; the smoke uses
explicit SIMULATED shapes and succeeds without public-data acceptance.

```powershell
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-demo --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --mask-2024 .cache/tyre-dataset-20261011.json --mask-2023 .cache/r026-proxy-public-20261013/eligible_input.json --output .cache/track-reconstruction-new
.venv/Scripts/python.exe -m apexsim.cli verify-track-reconstruction .cache/track-reconstruction-new
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-smoke --output .cache/track-reconstruction-smoke-new
```

For source-supported reconstruction runs, artifacts include original/registered lap arrays and native lineage, timing,
coefficients, arc tables, all projected/coarse-curvature predictions, candidate
scores, sensitivity and annotations. The manifest is written last. Portable
verification refits stored training inputs, replays selection/gates/predictions
and annotation projections without original caches. It establishes local
consistency, not provider authenticity. Native-source rebuilding remains a
separate archive/mask workflow. Bulk arrays stay ignored locally; compact
evidence and reports are version controlled. SIMULATED smoke cannot close R029.

Future accepted reference geometry does not establish longitudinal vehicle calibration,
complete closed-loop laps, a production track model or R3 maturity promotion.
