# R018 causal nominal/disturbance study

This protocol is pre-registered in the [implementation report](../../docs/verification/strategy-scenarios-report.md).
The published scenario catalog is [FIENI scenarios v1](../fixtures/fieni-scenarios-v1.json).
It records source results without treating them as synthetic training targets.

## Frozen study

Use the R017 three-lap model, pit window [0,1], epsilon=0.01 MJ, all three dry
initial compounds and every final supplied R017 checkpoint. Five cases: nominal,
zero dose before index 1, +0.6 wear before index 0, +0.6 before index 1 and +1.0
before index 1. Dose is dimensionless. These are PRIOR interventions, not paper
shock estimates. Inject immediately before the decision: no retroactive time,
fuel, mass, battery or pit edits. Return current wear in the normal observation;
no controller can receive the event before that boundary. Unsupported domain
interventions are rejected rather than clipped.

Methods: committed nominal R016 plan; causal optimizer following that plan until
the event and then solving an observed-state tiny continuation; greedy feasible
energy/early-pit rule; conservative reaction to the observed event by switching
to HARD (SOFT if already HARD), and every frozen SAC seed. The conservative
method follows the nominal physical controls and pit plan before a nonzero
observed event; after reacting it uses the recorded R016 greedy energy start
and has no scheduled stop. Zero-dose events do not trigger a replan or reaction.
The early-pit rule uses the same greedy energy start throughout. Pit masks still
enforce the required compound change; reachability projection remains explicit.

## Continuation and scores

The tiny reference is independent scalar/NumPy vertex enumeration over <=3
remaining laps. Fuel consumption fractions have [0.9,1.1] bounds and sum to
observed fuel divided by the original nominal allocation. Battery deltas sum to
negative observed battery; every prefix lies in [0,capacity]. No fresh full tank
or battery is assumed. Current compound/change/outlap/wear are retained. Discrete
plans satisfy the remaining global pit window and terminal required-change rule.
Only mass-independent wear and a concave/linear smoothed battery objective are
supported. Infeasible unclipped wear schedules are excluded and counted.
Candidate limits are checked before enumeration; failure gives no partial optimum.

For each method, reference the state it actually reaches at the event. Remaining
time regret is its post-event cost minus that state's best continuation. Nominal
references start at reset. A full-race difference against the combined causal
optimizer is signed and does not certify global optimality across different
prefix states. Keep both quantities separate. Model/smooth replay agreement
must be <=1e-8 s; reset reference agreement <=1e-6 s; resources <=1e-7; original
piecewise discrepancy must obey the R015 bound. Log all resource projections.

Nominal versus zero-dose actions/states match. Costs under a committed action
sequence must not decrease as wear is raised. Causal reoptimization cannot be
worse than its own unchanged feasible continuation within tolerance. In the
SOFT-start initial-shock case, the validated synthetic cubic makes an earlier
stop beneficial. These tests establish DIRECTIONAL_MATCH for the implemented
synthetic mechanism. Report SAC non-response/suboptimality without retuning.
No published-magnitude or real-race adaptation claim follows.

## Input/output and verification

Require an immutable R017 run with a verified manifest, config, environment,
all declared seeds, final-step update counts and finite inference checkpoints.
No training occurs. Input checkpoint/source hashes are checked before and after
evaluation. CI uses the existing R017 smoke run; full local evidence uses its
three-seed research run. Smoke is execution evidence only.

Planned CLI contract (not implemented in the continuation-foundation checkpoint):

```powershell
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
.venv/Scripts/python.exe -m apexsim.cli strategy-scenarios-demo --policy-run .cache/sac-research-20261008 --output .cache/strategy-scenarios-new
```

Output must be new and outside the input root. Save catalog, config/input hashes,
case records, rollouts, reference diagnostics and summary. Numerical validation
precedes writing; manifest is written last. Preserve failures and label legal-only
aggregates. All seeds and initial compounds are reported; no winner selection or
confidence claim from the small fixed scenario set. R018 completion is a reported
directional adaptation with tested causal boundaries; global maturity promotion
requires a separate R1 review.
