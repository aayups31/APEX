# R027/R028 — frozen forecasting explanation study v1

Preregistered 2026-10-30, before explanation/counterfactual outcomes. Classification:
**ADAPTATION**. Research only; no production promotion or causal intervention claim.

The [numerical implementation correction](FORECAST_EXPLANATIONS_NUMERICS.md)
records the first attempt's batch-rounding invariant failure and fixed FP64
linear/ridge accumulation plus fixed-shape neural inference. It changes no
scientific gate, input or fitted model.

## A. Current state

Research foundation R1; production kernel R0. R024, R025, R026 and R029 are DONE.
Baseline commit d12886fc35fe94538f9c3f8f5ca7d77b2d54630f.
The 19 forecasting/generalization tests pass. The existing reference command
`python -m apexsim.cli verify-tyre-forecast-benchmark .cache/tyre-forecast-research-20261012`
reproduces all ten checkpoints, all six families. Saved windows, native origin
metadata, training scaler and reference inventory were inspected. The full
544-test baseline is also running; a failure must be resolved before acceptance.

## B. Scope

Complete R027 (temporal perturbation explanations and faithfulness tests) and
R028 (constraint-feasible model counterfactuals and validity tests). The user's
explicit request schedules these two P1 rows before R030; see ADR0007. Return to
R030 afterwards. No model fitting, accuracy retuning, new telemetry acquisition,
UI, VSC causal-effect estimation, world model or simulator/planner integration.

## C. Sources and fixed inputs

- Todd et al., arXiv:2501.04067v1, sections 3.5 and 4.2:
  <https://arxiv.org/html/2501.04067v1>.
- Sood & Craven, arXiv:2102.11934v1, TIME, equations 2–8 and temporal windows:
  <https://arxiv.org/html/2102.11934v1>.
- Master guide sections 10–17; REPLICATION_STANDARD; TODD_2025,
  TYRE_FORECAST_BENCHMARK and TRACK_GENERALIZATION protocols.
- Frozen R025 reference summary:
  `c8f538d7ae46ec06a46d9af1b37fb9e4fe7429ac3c942845976fe2ccf189fe9f`.
- Frozen R026 evaluation summary:
  `f565de0903a71ca19a6dc753fc96ffeb82410d11c00e317bb071ee3fc02bec18`.
- Inventory anchors (recorded before study outcomes): R025 manifest content seal
  `77e0de71402a8ca9a5c9a73afac0540d68e435d6c1211b9eea19b3b595559616`;
  R026 manifest content seal
  `7584f03bf8d8b54c9b9106451b063a9e2f019f0e00aa26fbc717b6a54a8eaaab`.
- R025 training windows only supply donors, scaling and marginal support ranges:
  2024 Bahrain/Australia. All ten checkpoint bytes remain unchanged. XGBoost is
  the previously validation-selected primary family; no new family selection.
- Evaluation: the R026 2023 Bahrain/Australia (seen circuits), Monza/Singapore
  (unseen circuits) native windows. These are previously inspected development
  events, not a fresh confirmatory benchmark. Permanent nine-event reservation
  remains untouched and checked before window payload access.

Select 16 origins per event/driver by sorted SHA256 of the source identity,
greedily retaining at most two per sequence and spacing origins by at least
eight native samples. Require a same-sequence next-sample origin for the nearby
stability diagnostic. Selection uses metadata only, no predictions, targets,
importance or success labels. Record every selection and shortfall. Eight cells
give at most 128 origins. Smoke uses at most two per cell and is ineligible for
public closure. No replacements after inspecting outcomes.

## D. Equations, interfaces and implementation

Add `research/forecast_explanations.py`, an immutable study runner/verifier,
CLI commands, tests, model card and acceptance evidence. Preserve existing APIs.
Predictors accept histories shaped (N,8,14), immutable static categories and
return (N,3,4) forecasts in kJ. They never receive future targets. Retain raw
predictions and disclose the existing nonnegative output projection separately.

### R027: grouped temporal perturbations

Twelve fixed players: four consecutive two-sample windows (oldest to newest),
crossed with kinematics {speed, longitudinal/lateral acceleration, steering,
heading rate, geometry speed}, controls {throttle, brake}, and four past energy
proxies. Static identity, dt and position lag are immutable. Units remain SI/kJ.

Donors are training-only, same driver and compound, selected deterministically
by source-key SHA256 with salt 2728. Use eight distinct donor sequences; the first
four rank players, the other four audit that ranking. If fewer than eight
sequences exist, abstain. Donor track can differ; record it. No future donor
target is used. Block replacement preserves within-block ordering but may break
cross-feature or boundary consistency: this is a model diagnostic, not a feasible
trajectory. Report constraint failures of diagnostic perturbations.

For player p and donor d, replace its block and evaluate
`A[p,h,w] = mean_d abs(f(x)[h,w] - f(replace(x,p,d))[h,w])`.
Rank by mean over all three horizons/four wheels, stable player-index tie break.
Store signed deltas and per-wheel/horizon scores, not only a heat map. Independently
audit on the disjoint donor half. Compare held-out single-player effects in the
top three against all-player random expectation and the bottom three. Also
evaluate joint top-three deletion and insertion against 16 seeded random
three-player masks on audit donors. Insertion starts with all 12 players replaced
by one donor, then restores selected players. Keep dt/lag/static from the origin.
Report changes in squared forecast error only as a secondary, target-dependent
diagnostic; it cannot determine the explanation or cohort.

Reliability gate per origin/checkpoint: nonzero rank signal >1e-6 kJ, Spearman
rank/audit correlation >=0.5, held-out top-three mean effect greater than random
expectation by >1e-6 kJ, and joint deletion at least random-mask mean. Otherwise
return `ABSTAIN_UNSTABLE_OR_UNFAITHFUL`; do not silently return confident rankings.
Missing donor support returns `ABSTAIN_DONOR_SUPPORT`. Report nearby (+1 sample)
top-three overlap and same-family seed overlap separately, without treating seeds
or overlapping origins as independent races. Global importance averages origins
within event, then events within seen/unseen strata. Report 500 sequence-cluster
bootstrap intervals conditional on these fixed events (seed 2728); no population
claim or hypothesis-testing/FDR replication.

This adapts TIME's block permutation concept. It omits TIME's adaptive window
search and FDR discovery, uses output dependence for local ranking instead of
target-loss importance, and includes independent-donor tests. It is not exact
TIME, Shapley attribution, additive causal allocation or attention explanation.

### R028: finite, coupled scenario counterfactuals

Enumerate the Cartesian product of speed factors
`[.8,.85,.9,.95,.975,1,1.025,1.05,1.1,1.15,1.2]` and throttle offsets
`[-.2,-.1,0,.1,.2]` (55 scenarios including identity).
For each complete eight-sample history, transform
`v'=a*v`, `ax'=a*ax`, `geometry_speed'=a*geometry_speed`,
`heading_rate'=a*heading_rate`, `ay'=a*a*ay`, `steering'=steering`,
`throttle'=throttle+b`. Brake, dt, lag, static categories and source identity
remain fixed. Uniform speed scaling preserves the linear derivative relation;
curvature omega/geometry_speed is unchanged. Recompute every past wheel energy
using the shared R024 proxy, fixed mass900kg/wheelbase3.6m and its other declared
priors. Never edit an energy input independently. Identity returns the original
history exactly after checking its source consistency.

Reject (do not clip) nonfinite values, throttle outside[0,1], non-boolean brake,
dt outside(0,.5], lag outside[0,.35], speed outside[5,105]m/s, |ax|>30m/s2,
|ay|>60m/s2, |omega|>1.5rad/s, |steering|>.6rad, geometry/speed ratio outside
[.5,1.5], or any *unprojected* prior wheel load below50N. Require
`ay=-v*omega`, `steering=atan(3.6*omega/geometry_speed)` and proxy-energy
consistency with rtol5e-5/atol5e-6 (float32 storage tolerance). Require every
feature inside the training-only marginal min/max envelope, with that same
numerical tolerance; no fitting to evaluation. Original inconsistent or
out-of-support histories abstain. This is algebraic/kinematic/proxy feasibility
within declared priors, **not** validated actuator, friction-circle, complete
track-path, tyre thermal, race-control or real-car feasibility. Those are UNKNOWN
until later vehicle/closed-loop evidence. No recommendation is issued.

Scalar score is mean projected forecast energy over matched horizons/wheels
(kJ/sample; not cumulative energy or power). Goal: reduce it by at least
`max(0.1*baseline,0.01kJ)` without using future actual values. Choose the feasible
crossing candidate of lowest `abs(a-1)/.2 + abs(b)/.2`, deterministic (a,b) tie
break. Optimal means *within these 55 candidates only*. Exhaustive enumeration is
the exact oracle. Compare speed-only and throttle-only subcatalogues. For primary
XGBoost also require the same candidate to cross each frozen seed's own target;
report robust success separately from single-checkpoint success.

Every success is independently rechecked for source identity/timing immutability,
equations/bounds/support, target crossing and absence of a cheaper crossing
candidate. No feasible crossing returns a reasoned abstention, not a fabricated
scenario. Expose candidate rejection reasons, complete raw/projected forecasts,
per-wheel/horizon changes, cost and catalogue margin. No global optimum or
causal VSC effect can be inferred from this exercise.

## E. Evaluation and stopping gate

- Hand fixtures: known sparse-lag additive predictor must recover its two true
  players, constant predictor must abstain; irrelevant players have exactly zero
  effect. Hand speed scaling verifies ay quadratic, curvature unchanged and
  energy recomputation against the scalar reference. Exhaustive tiny CF oracle
  verifies minimality, ties, impossibility and joint-seed crossing.
- Leakage/guard tests: no target passed to predictors; changing future targets
  cannot change rankings/CFs; training-only donors/support; native keys/sequence
  and static identity checked; protected event refused before NPZ/checkpoint read.
- All six real checkpoint families and persistence/trend are evaluated; all seed,
  event, seen/unseen and abstention results retained. At least64 public origins,
  at least8 per event/driver, all four events, with no outcome-based replacement.
- 100% of emitted CF successes must pass independent feasibility/crossing and
  finite-catalogue optimality replay. Unstable explanations must abstain.
  Neither a 100% CF success rate nor universal model faithfulness is required:
  failures are findings, not grounds for changing thresholds.
- Minimum useful public evidence: at least one reliable primary XGBoost
  explanation and one jointly crossing, seed-robust XGBoost counterfactual in
  each of the seen/unseen strata. A negative result is retained if this fails;
  it cannot be repaired by loosening gates or dropping origins in this version.
- Immutable output, complete file inventory/hashes, source/checkpoint/protocol
  seals, portable checkpoint reload, full deterministic metric/decision replay,
  relocation and tamper tests. Numeric prediction replay rtol1e-6/atol1e-7;
  report maximum differences. Smoke cannot be resealed into public acceptance.
- Full regression/lint and Python3.11/3.12 CI pass. Reports/cards/backlog reflect
  limits. Close both rows only with all these implementation and audit gates;
  production remains R0 and foundation review remains R1.

## F. Risks

Public energy is a model-based PROXY, not measured energy. Correlated proxy
inputs may dominate explanations; temporal splices can be off manifold.
Marginal support is necessary but not sufficient for joint physical support.
Short native histories, only two circuits per novelty stratum, reused development
events, few donor sequences for some compounds and CPU budget limit inference.
This study measures model dependence and bounded what-if scenarios; it cannot
establish tyre degradation, race strategy benefit or causal interventions.

## G. Execution order

1. Commit/push protocol and scheduling ADR before observing new outcomes.
2. Implement and test temporal perturbation equations and loaded predictor.
3. Commit/push coupled scenarios, constraint checks and exact finite oracle.
4. Connect sealed runner, replay verifier, CLI and simulated integration tests.
5. Freeze metadata-only cohort; run public study with unchanged models/inputs.
6. Audit outputs and failures, run full regression/CI, publish evidence/cards.
7. Mark accepted rows DONE, commit/push; return next to R030.
