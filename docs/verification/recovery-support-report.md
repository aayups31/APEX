# R037/R038 continuous recovery and support supervision

2026-11-03. **R037 complete. R038 public evaluation in progress.**
Research foundation R1 and production kernel R0 remain unchanged.
[R037 protocol](../../research/protocols/MULTILAP_RECOVERY.md),
[R038 protocol](../../research/protocols/SUPPORT_FALLBACK.md),
[equations](../../research/equations/RECOVERY_SUPPORT_V1.md),
[data contract](../data/closed-loop-recovery-support.md) and
[component card](../models/recovery-support-v1.md) define the conditional scope.

## Baseline and frozen inputs

Base9e77601723a16eaab0df7453541ab96ac2311c53 passes713 tests on Python3.11/3.12
and all artifact workflows in [CI41355474238](https://github.com/aayups31/APEX/actions/runs/41355474238).
The fresh Windows/Python3.12 local baseline passes713 tests in1834.43s with the
same two dependency warnings, from `apex_engine`, single-thread BLAS. The baseline
log is retained locally as `.cache/r037-r038-baseline-20261101.log`.
No existing test, timeout, dynamics or controller acceptance threshold was relaxed.

A fresh complete R036 synthetic pipeline and replay pass, seal
ccb3c8b922b832934ad01de057ad943e890f2f4bcb5b02fb95e185d5103f6b7a.
Its known smoke improvement failure remains explicit; execution is not superiority.
The accepted public R036 parent seal is
2f549c5224413fde09f5d99af2043305c5cac81ce49daa9afd9647a2be4264ae.
The [R037 source freeze](recovery-input-freeze.json) and
[exact initial-condition catalog](recovery-condition-catalog.json) were pushed in
34617b1 before the public multi-lap test. No R036 weights, pace, maps, chassis
equations or protected benchmark events change.

## Synthetic checks

Seven continuous-runner tests pass, including exact first-lap parity with R036,
unwrapped seam continuity, memory-preserving actuation, repeated pulses and sustained
recovery accounting. Fifteen supervisor tests pass, including independent sorted
quantiles, both sides of every feature axis, a documented in-box blind spot,
ten-command release hysteresis, nonfinite/overflow rejection, latched abstention
and transparent fallback independent of faulty learner features. A new test's
initial strict floating-point comparison saw0.15000000000000002rad versus.15rad;
the test now uses1e-14rad tolerance while matching the unchanged controller exactly.

The complete R037 synthetic study passes all14 required three-lap cases plus the
retained large challenge, with103 independent held-action checks. All15 runs
regenerate exactly. Smoke cannot close public R037. The first R038 smoke campaign
passes its20 physical-case and6 hard-abstention catalog, including every detection,
release, refinement and independent gate. Subsequent numeric overflow hardening
does not change its envelope formula/thresholds; the hardened implementation must
pass fresh pipeline/regression checks before closure. The hardened campaign now
passes fresh full26-case regeneration with zero difference. All10 artifact tests
pass in574.26s, covering the full physical smoke pipelines, portability, leakage,
protected events, changed data/thresholds/ledgers and resealed false completion.
The [development verification receipt](recovery-support-development.json) binds
the baseline and32 new targeted tests to the complete synthetic replay receipts.
All745 tests and every artifact workflow pass Python3.11/3.12 in
[implementation CI41359598572](https://github.com/aayups31/APEX/actions/runs/41359598572)
at6d4b3b4. Test runtimes are615.13s/651.87s respectively; the
[captured CI receipt](recovery-support-ci.json) preserves both complete jobs.
Actual-copy boundary inspections also reject changed bytes, reserved events,
resealed omitted cases and a resealed changed cutoff. All16 outside-axis points
are detected while the constructed joint in-box corner remains undetected, an
explicit structural blind spot. These constructed faults do not establish
real-world OOD accuracy or a certified safe region.

## Pending public evidence and next gate

R037's primary numerical campaign now passes every declared gate. The
[primary summary](recovery-primary-summary.json) binds all
[compact primary results](recovery-primary-results.json), including28 required
five-lap runs and the separately retained large-challenge failure. All32 required
small pulses begin a sustained two-second matched-path recovery window within.8s.
Maximum required station-grid error is.381478m and P95.237540m; largest last-minus-
first lap RMSE increase is.000158607m. These are conditional reference-map metrics.

| Nominal macro station RMSE(m) | Lap1 | Lap2 | Lap5 |
|---|---|---|---|
| R035 transparent | .101435780 | .101407471 | .101421666 |
| Frozen R036 learned | .077451083 | .077225339 | .077221098 |

All236 independent physics checks pass. The complete6695-interval five-lap
held-action audit differs by at most.009738753m in XY and.000030257m/s in body
velocity. Across four complete-horizon refinements, maximum common-station XY
difference is.000740098m, speed difference.000207069m/s and finish difference
.000002726s. Numerical agreement does not establish surveyed-map or real-car accuracy.

The preregistered.3rad large challenge exits the5m experiment reference corridor
at7236.045515m of progress. Its prefix and attempted final action are retained;
this is not replaced by a successful run or credited as recovered. Full29-case
[scientific regeneration](recovery-public-replay.json) reproduced all saved arrays
with zero difference. The [independent boundary inspection](recovery-boundaries.json)
checked 189,224 held actions and rejected corrupt, incomplete and reserved-event evidence.

R037 runs all four frozen source conditions across five continuous laps with both
controllers and both pulse signs, plus nominal timestep refinements and the large
challenge. R038 requires its accepted, fully regenerated parent before fitting the
public detector. Detector centers/ranges use training features only; cutoff uses
validation episodes only. Parameters must be pushed before R038 test execution.

Task completion still requires full public catalogs, retained unsafe prefixes,
refinement, independent complete-horizon physics, complete scientific regeneration,
source-bound publication and full regression/CI. No DONE status is inferred from
the implementation or synthetic results. Real-car pace, measured steering,
unknown-physics recognition, race-distance resource dynamics and formal maturity
promotion remain unavailable. R039 thermal physics follows these scoped gates.

The final implementation passed 748 local tests. The [frozen R038 detector](support-detector.json) and its [source seal](support-detector-freeze.json) were pushed in d7bbc95 before the public fault campaign.
