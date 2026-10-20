# R029 observed-support reference geometry v2

Historical result:strict v2 is rejected for unsupported holdout anchors; v2.1
is rejected for one unfiltered chronological curvature-proxy failure. Both
decisions remain preserved. [V3](reference-geometry-v3.md) completes R029 under
a separately preregistered source-support method and additional confirmation.
See the
[protocol](../../research/protocols/TRACK_RECONSTRUCTION_V2.md),
[equations](../../research/equations/OBSERVED_TRACK_SUPPORT_V2.md), and
[decision record](../architecture/adr-0006-observed-track-support.md).
The [v1 source failure](../verification/track-reconstruction-report.md) stands.

V2 fits observed native vertices across ten training laps per circuit, uses ten
validation laps to choose one of six frozen candidates, then evaluates twelve
separate2023 geometry-development test laps. Bahrain/Monza2024 train/validation
and2023 holdout are separate events; validation shares the training event with
a different driver. Development-event reuse is disclosed. Nine reserved whole-event
benchmarks remain protected. The original eligibility mask and source seals bind
all64 laps. Source scale is0.1m per native XY unit; no geographical north is inferred.

Missing native intervals remain unsupported at the original0.75s limit. Only
supported timing anchors are interpolated. Coarse curvature windows crossing
missing intervals abstain with NaN UNKNOWN plus a boolean mask. All observed
positions are scored. Every10m station requires three training-lap donors;
leave-one-lap normal offsets and source coverage quantify conditional sensitivity
and missing-data support without claiming calibrated confidence or survey truth.

The fitted object is a reference RACING TRACE. Rigid full-lap pose alignment makes
errors registered-shape errors. Width, validated elevation, surveyed centerline,
official DRS and full pit route remain UNKNOWN. Training-source timing annotations
are projected with lineage/support/spread. Research ancillary requests refuse
implicit12m/zero/false assumptions. Production race sampling is unchanged.

Run from the checkout using the existing immutable inputs and fresh output paths:

```powershell
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-v2 --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --mask-2024 .cache/tyre-dataset-20261011.json --mask-2023 .cache/r026-proxy-public-20261013/eligible_input.json --stage development --output .cache/track-geometry-v2-development-new
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-v2 --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --mask-2024 .cache/tyre-dataset-20261011.json --mask-2023 .cache/r026-proxy-public-20261013/eligible_input.json --output .cache/track-geometry-v2-research-new
.venv/Scripts/python.exe -m apexsim.cli verify-track-reconstruction-v2 .cache/track-geometry-v2-research-new
.venv/Scripts/python.exe -m apexsim.cli track-reconstruction-v2-smoke --output .cache/track-geometry-v2-smoke-new
```

Development stage never loads geometry test laps and cannot close R029. Simulated
smoke cannot claim public source identity or acceptance. The envelope records
summary/file hashes and is written last. Save native XY/times/parents, coefficients,
arc tables, every projected position, missing interval/curvature masks, all
candidate scores, per-lap metrics, donor matrices, sensitivity and annotations.
Portable verification refits stored inputs and reproduces arrays/decisions without
the original archives. Annotation projections replay from saved source positions;
rebuilding their native brackets still requires original verified archives.
Hashes establish local consistency, not provider authentication. Bulk arrays stay
ignored locally; compact evidence and reports are version controlled.

Accepted reference geometry alone does not validate vehicle dynamics, complete
closed-loop real laps, production track promotion or an R3 maturity claim.
