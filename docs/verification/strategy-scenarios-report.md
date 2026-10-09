# R018 nominal and disturbed strategy scenarios

- Date: 2026-10-08; baseline main 4c0bdf7
- Status: DONE (closed 2026-10-09); global maturity before/after implementation R0

## A. Current state

R012-R017 are complete: reviewed equations, hand fixtures, independent tiny
references, smooth maps, bounded local solver and frozen three-seed SAC training.
Fresh full baseline: 379 passed, two existing dependency warnings, 195.29 s.
Reference solver acceptance reran at .cache/r018-baseline-solver-20261008:
summary hash 81bd671411801edee356730aee7e98ae77c6dffcb5aaed632274fd655ec0aafb,
maximum independent tiny regret 5.684341886080802e-14 s. Artifacts inspected.
Existing untracked artifacts are preserved. No training or source refactor is planned.

## B. Scope

R018: reconstruct the published nominal/disturbance specification and reported
metrics, then execute a declared three-lap synthetic directional analogue with
frozen R017 policies, rules and a causal continuation oracle. R016's nominal
optimizer supplies a committed plan. Add continuation planning from an observed
state; never forecast the unrevealed shock. Completion requires the directional
report, not matching unavailable confidential maps or making SAC outperform rules.
Keep production and world-model promotion out of scope. A later R1 review must
assess its own gates; this row's completion does not automatically promote maturity.

## C. Sources

Master guide sections 7,10-13,15-17; replication standard; FIENI equation review;
R015-R017 protocols and source. Paper arXiv:2512.21570v1, local SHA-256
fc609aa9dcff9179d5e6cba8ce96eb7785f8db45daeef2fc6c4aad32ad133270.
Pages 10-12 were extracted and rendered for visual review, including Figures
6-8 and Tables 3-4. Catalog published setup/results separately from synthetic
parameters. Exact initial resources, fitted map parameters, shock amplitude and
fine timing are unavailable; do not infer them from plots or use printed regret
as an acceptance target. No original-model magnitude replication is possible.

## D. Implementation

Add a pure, bounded continuation vertex oracle (<=3 remaining laps,
mass-independent wear, affine fuel and concave battery). Its initial resource
constraints use the actual observed fuel/battery/mass, compound-change and
previous-pit state, not reset values. Exhaust all allowed pit plans and resource
vertices; reject unsupported wear/candidate budgets without clipping or partial
optima. Compare nominal reset results with the independent existing reference
and R016. Replay continuations through the actual model and independent smooth map.

Add an atomic nonnegative wear intervention before a decision: only wear changes;
completed time, resource states and previous actions remain unchanged. Reject
nonfinite, negative, terminal or outside-domain shocks before mutation. Controller
calls receive current observations/masks and an event only when it occurs.

Freeze five cases: nominal; zero dose at index 1; wear +0.6 at index 0; wear +0.6
at index 1; wear +1.0 at index 1. Apply each to initial SOFT/MEDIUM/HARD, with the
unchanged R017 model, smoothing and pit window [0,1]. These doses/timings are
synthetic PRIORS and are not a rescaling or digitization of paper lap 22.
Methods: committed nominal optimizer plan; causal replan only after observing
the event; greedy energy/early-pit rule; conservative hard-tyre reaction (SOFT
if already HARD to ensure a change); every supplied frozen SAC seed. The
conservative method follows the nominal plan before the event and pits at the
first allowed observed event, then follows greedy energy with explicit masks.

At the event boundary (or index 0 for nominal), compute each method's independent
optimal continuation from its own observed prefix state. Report remaining-time
regret against this matched state. Also report signed full-race gap against the
combined causal optimizer, explicitly not a global regret certificate: other
methods may have different pre-event states. Save all failed episodes and both
requested/applied actions; do not average failures away.

Verify a complete R017 input manifest, exact frozen config/environment and
checkpoint hashes before loading. Research uses existing seeds 11/23/37; CI
uses its existing R017 smoke run (seed 11), clearly tagged as smoke. No new
gradients, reward tuning, best-checkpoint selection or disturbance training.
Save input/source snapshots, all cases/rollouts, continuation counts and scores,
runtime, outcome labels, and final immutable manifest. Hash inputs before/after.

## E. Gate

Tests: current-state hand continuation optimum/resource vertices; reset parity;
wear atomicity and reset timing; no pre-event information leak; zero-dose
equivalence; malformed states and unsupported family/budget rejection; independent
smooth/model replay; manifest tampering and checkpoint/config rejection; immutable
artifact integration. Objective agreement <=1e-8 s, reference/adapter reset
agreement <=1e-6 s, physical residual tolerance 1e-7 and R015 smoothing bound.
No extra constraints or reward penalties are introduced to conceal poor policies.

Directional acceptance: fixed-action cost is nondecreasing under increasing wear;
zero-dose has no trajectory effect; causal continuation is no worse than keeping
its own committed feasible continuation (within 1e-8 s), and attains its matched
reference; the synthetic SOFT-start +0.6 initial shock advances the optimal stop
relative to nominal (the cubic wear penalty exceeds the fresh MEDIUM offset).
SAC adaptation/quality is measured, not required to improve. A non-response or
worse score is retained as a negative/inconclusive result. Published metric
comparison stays INCONCLUSIVE; no numeric paper tolerance is invented.
Full three-seed research evidence, regression/lint and Python 3.11/3.12 CI must
pass before closing R018. No production promotion follows from directional tests.

## F. Risks

Small task versus full-race scenario; private maps; untrained wear domain; masks
concealing learned legality; different pre-event states making global-gap claims
invalid; aliasing from resource projection; numerical vertex tolerances; finite
candidate budgets and dependency access. Rank variability across three frozen
seeds is descriptive, not a calibrated confidence interval or stochastic forecast.

## G. Order

Baseline/source review; freeze catalog/protocol; continuation and intervention
tests; artifact/CLI; targeted smoke and direct-main checkpoint; frozen research
evaluation; full regression/CI; evidence and backlog closure; final main push.

## H. Continuation-foundation checkpoint

Implemented `continuation_reference.py`: independent scalar/NumPy enumeration
from the observed state, including partially spent battery prefix bounds,
original nominal fuel allocation, inherited outlap/change state, global pit
window, candidate-budget refusal and counted exclusion of unclipped-wear
infeasible plans. No optimizer graphs or projected transitions enter its objective.
Implemented `strategy_disturbances.py`: atomic current-wear intervention with
finite/nonnegative/domain checks; completed history and resources are retained.
Existing R016/R017 implementation and frozen checkpoint files are unchanged.

Targeted validation: 28 passed. Tests cover all-compound reset-reference parity,
one- and two-lap hand costs, partly spent battery vertices, nine independent
smooth-map/model continuation replays, inherited terminal change legality,
unsupported-family/budget rejection, unclipped-wear exclusions, atomic wear
intervention before/after a step, and terminal rejection. Fixed-plan shock costs
are nondecreasing and matched causal continuations do no worse; the initial SOFT
shock advances the stop. Repository Ruff and diff whitespace checks pass.
Full regression: 404 passed, two existing dependency deprecation warnings,
122.28 s, at `.cache/r018-continuation-regression-20261008`. That run collected
the initial 25 new tests; three additional fixed-plan directional tests were
added during execution and passed in the final 28-test targeted run. No engine
code changed after full regression began. GitHub CI will exercise all 407 tests.

R018 remains IN_PROGRESS. This checkpoint does not evaluate the frozen SAC
checkpoints under shocks and does not establish policy adaptation. Next: causal
controller/scenario runner, immutable R017 input validation, artifact CLI and CI
smoke step, then all three frozen research seeds with full saved rollouts and
matched-state scores. The CLI in the protocol is a planned contract until that
runner is implemented. Research/build completion counts and R0 maturity remain
unchanged.

## I. Scenario-runner checkpoint (2026-10-09)

Implemented causal controller comparisons, frozen-input validation, scenario
rollouts and the `strategy-scenarios-demo` CLI. Controllers see current state and
an event only at its boundary. Zero dose does not trigger a replan/reaction.
The nominal R016 plan is committed until an event; causal replanning replaces
only its remaining actions. Conservative reaction follows nominal physical
actions before the event and greedy requested energy afterward. Every recorded
lap is checked against independent model history and the symbolic smooth map.
Matched-state continuation regret is separate from signed full-race causal gaps.

Exact R017 artifact inventory, hashes, source compatibility, configs, environment,
inference checkpoint kind, finite parameters and final update counts are checked.
Evaluation preserves weights, updates and local policy RNG and rechecks input
and implementation hashes. No new training, retuning or checkpoint selection.
Output saves all cases and failures, requested/applied controls, reaction metrics,
descriptive case rankings, projection magnitudes, provenance and manifest last.

Initial smoke: 75/75 legal episodes, all directional gates pass, maximum smooth
replay error 2.842170943040401e-14 s. This is execution evidence only and preceded
the addition of reaction/ranking metadata. Final targeted run: 39 passed in
11.54 s (28 continuation/intervention plus 11 scenario/input/artifact tests).
Tests reject altered bytes, config, update count, checkpoint kind, nonfinite
weights, extra files and traversal names before creating output. CI now runs the
scenario CLI against its freshly generated R017 smoke artifact. Full frozen
research study, regression and CI results are still required before R018 closure.

## J. Frozen research results (2026-10-09)

Run: `.cache/scenarios-research-20261009`, implementation b3989a8; unchanged
R017 input `.cache/sac-research-20261008`. All five cases, three dry starting
compounds and seven methods: 105 attempted/105 legal episodes, 315 laps, zero
new training steps. All directional, causality, zero-dose, nominal action parity
and input/policy immutability gates pass. Maximum independent smooth replay
error 2.842170943040401e-14 s. Research summary content hash:
55ba3ab9e123cf5696ca153fa8ca905cb519e20cf78dc0dc1140a458a9e684eb.
Manifest content hash:
c5ea738f28a85bc961df9676ba9075dc79885a868943e911745dfcc5782a947a.
The saved catalog, config, plans and all rollouts were inspected.

| Method | Mean matched-state regret (s) | Mean signed full-race gap to causal (s) |
|---|---:|---:|
| Causal replan | -1.33e-14 (roundoff) | 0 |
| Committed nominal | 0.133709 | 0.133709 |
| Greedy energy/early pit | 0.056615 | 0.601114 |
| Conservative HARD | 6.222182 | 6.222182 |
| Frozen SAC 11 | 0.428096 | -0.508962 |
| Frozen SAC 23 | 0.737207 | -1.196247 |
| Frozen SAC 37 | 0.719177 | -1.214376 |

Each mean covers all 15 fixed cases for its method; zero-dose repeats nominal
and is retained as preregistered. These are descriptive scores, not uncertainty
estimates or statistically independent trials. Different policies reach different
pre-event states: negative signed full-race gaps do not mean beating the optimum
of the same state. The combined causal comparator keeps its nominal prefix
until the event; it is not a hindsight full-race optimizer.

All three SAC seeds changed requested energy at the boundary in all nine
nonzero-shock cases, but none changed its pit choice compared with nominal.
This measures requested-action response; reachability projection may alter
applied energy. In the SOFT-start +0.6 initial case, causal replanning advances
the stop from index 1 to index 0; the committed and all SAC schedules keep the
later stop. Their matched regrets are 2.005642 s (committed), 2.055794 s (seed
11), 2.014408 s (23), 2.035419 s (37); causal and greedy early pit attain zero.
Worst SAC matched regret by seed: 2.961744, 3.157848, 3.153955 s. None of the
three seeds beats the greedy rule's mean matched-state regret. Keep this negative
result without disturbance retraining or retrospective checkpoint selection.

Measured mean decision runtime per lap is 0.000688/0.000540/0.000504 s for
SAC seeds 11/23/37, and 0.000692 s for causal replanning (averaged over all
45 laps, including boundaries without a replan). Nominal R016 planning runtime
is saved separately. Model/reference bookkeeping is excluded from decision time.
The study ran alongside full regression on the same CPU; timing is descriptive,
not an isolated performance benchmark. Python 3.12.12, Torch 2.14.0+cpu,
NumPy 2.5.3, CasADi 3.7.2; all three thread limits and Torch threads are 1.

Validation: 39 targeted tests passed in 11.54 s; full regression 418 passed,
two existing dependency warnings, 93.84 s; repository Ruff and whitespace
checks pass. Python 3.11/3.12 CI run [37882697815](https://github.com/aayups31/APEX/actions/runs/37882697815)
passed every step, including the new frozen-policy disturbance artifact check,
on implementation b3989a80c8348d7e472e56ed33cf6032c952cd36.
Outcome: DIRECTIONAL_MATCH for the synthetic adaptation; published magnitude
comparison INCONCLUSIVE because the original maps/resources/shock amplitude
are unavailable. Global maturity remains R0 pending the separate R1 gate review.

## K. Closure and next work

The [machine evidence](strategy-scenarios-evidence.json) preserves the original
R017 training reference, full R018 catalog/config/nominal plans/105 rollouts,
summary/manifest, local validation and successful CI job/step results.
Machine-evidence content hash:
987752e197d68d610f77898fd182ed066404001a05f0a3d965677577055fa560.
R018 is complete as a declared directional adaptation, with policy limitations
and unreplicated published magnitudes explicit. Research backlog: 18/73 DONE,
55 remaining. Build backlog remains 13/66 DONE, 53 remaining.

Next: a separate R1 evidence-gate review of equations, unit maps, independent
tests and scenario reconstruction, with an explicit promotion or remaining-gap
decision. Then R019 immutable historical-event manifests and R020 untouched
benchmark event selection establish the data boundary for R2 fitting. No paper
numeric replication, real-race calibration, world-model validation or production
policy promotion is implied by R018 closure.
