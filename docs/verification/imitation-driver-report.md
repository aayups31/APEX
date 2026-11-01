# R036 conditional imitation driver

2026-11-01. **IN_PROGRESS: training frozen; final held-out evaluation pending.**
Foundation R1 and production kernel R0 remain unchanged. The
[protocol](../../research/protocols/IMITATION_DRIVER.md),
[source/sequence ADR](../architecture/adr-0008-conditional-imitation.md),
[data contract](../data/imitation-driver.md),
[model/run card](../models/imitation-driver-v1.md) and
[equation map](../../research/equations/IMITATION_DRIVER_V1.md) define the scope.

## Baseline and source

Base `3b83de4b2c12aa514e18622af8e81e43a56dab8f` passed690 tests on Python3.11/3.12
in CI41244984366. The new local baseline produced689 passes and one pre-existing
offline-Jolpica subprocess timeout. Its traceback reported a negative remaining
timeout during the clock/date change; its82330.38s elapsed value is unusable as a
compute measurement. The unchanged isolated test passed in21.82s. No timeout or
source behavior was relaxed. A final full regression is required for closure.

A fresh R035 disturbed-circle reference passes, seal
`89d42bea396787ed2f518ae1968c8665ad7bbedd0fcb6e03dc01dd89e84583df`.
R035 calibration replay passes unchanged. R036 prepared-source seal:
`44b927325c958198f3239000957dc6970b79ef8afa98a0d9d53d534ad95e963b`.
Its parent is the accepted conditional R035 study, not calibrated real-car physics.
All9 protected benchmark events remain untouched.

## Frozen training result

Development seal `69ac56b7364119fee1dd0a5ee2277e0b99356b0a8116a4e892c19871b7f1dfc2`.
The [full development results and weights](imitation-development.json),
[development summary](imitation-development-summary.json) and
[source condition catalog](imitation-condition-catalog.json) were pushed in
`331863e` before any R036 held-out learner evaluation.

All action labels are **SIMULATED expert steering corrections**, not measured
human actions.2023 Bahrain/Monza conditions train;2024 Bahrain validates;2024 Monza
tests. There are16 original expert episodes with22,600 labelled states, plus16
learner-executed training episodes with another22,600 labels. Training-only weighted
means/scales and equal collection-round/condition weights prevent row-density or
validation/test leakage. Source/driver IDs and absolute XY/station are not features.

Validation chooses a.10s known-map feedforward preview. Its expert lateral MSE is
.004105893534m². Four genuine supervised models compare linear/quadratic ridge and
two penalties. The selected initial behavior-cloning model has45 coefficients,
degree2 and alpha1e-8; validation MSE.004105885401m². The best linear model gives
.018548433873m². Stronger quadratic regularization gives.186228874628m²; this poor
candidate is retained rather than hidden. The aggregated checkpoint gives
.004105885401m² and adds no meaningful validation improvement, so initial BC is
retained. Every candidate and all68 development rollouts are preserved.

The improvement of the analytic preview expert is separate from the student's
ability to imitate it. A compact quadratic model can represent this analytic
target almost exactly. This is controlled conditional imitation infrastructure,
not discovery of new driving knowledge or superiority to the expert.

## Verification and stopping gate

Eight core policy tests, seven split/fit/gate tests and eight artifact tests pass.
Synthetic development replay reproduces all34 paths exactly; independent scalar
features match and QR versus primary-SVD prediction difference is7.75e-16rad.
The complete synthetic evaluation/replay also passes, with explicit
SIMULATED_EXECUTION_ONLY status and no public-task eligibility. Portable artifacts,
genuine training, frozen model selection, actual reserved-event guards, changed
payloads and resealed false completion are tested.

Before final test execution, all source-bound development dynamics and independent
fit/selection equations must replay. The frozen final policy then competes with
R035, expert, linear and initial BC on the complete matched eight-case nominal/
disturbed test catalog, followed by four timestep refinements and independent
held-action replay. Duplicate checkpoint identities are disclosed. The task can
close only with at least10% nominal macro tracking improvement, each-driver gains,
unchanged pace/physical limits, complete stable laps and every numerical gate.

## Limits and next dependency

Public steering/body lateral measurements remain unavailable. Generic vehicle
priors, supplied maps/localization, existing development-event history and the
large R035 source-pace shortfall remain. This learns steering only; longitudinal
control stays transparent. A bounded correction does not establish OOD detection,
fallback or multi-lap recovery. R037/R038 remain the next broader evidence gates.
