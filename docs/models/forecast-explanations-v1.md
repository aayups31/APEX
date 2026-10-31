# Frozen forecast explanations and bounded scenarios v1

R027/R028 are research **adaptations** of temporal perturbation and counterfactual
ideas. The [protocol](../../research/protocols/FORECAST_EXPLANATIONS.md),
[numerical correction](../../research/protocols/FORECAST_EXPLANATIONS_NUMERICS.md),
[equation map](../../research/equations/FORECAST_EXPLANATIONS_V1.md) and
[acceptance report](../verification/forecast-explanation-report.md) define scope.

The engine can inspect a saved linear/ridge/XGBoost/GRU/LSTM/TFT checkpoint or
persistence/trend baseline without retraining. Inputs are eight causal native
samples, immutable driver/compound/track categories and labelled physical/proxy
features. Outputs are four-wheel proxy energy at1/3/5 native sample horizons.
Future actual energy does not enter explanation ranking or scenario selection.

R027 reports three feature groups across four contiguous history blocks. Four
training donor sequences rank model sensitivity; four different sequences audit
it. Tests compare ranked against random deletion/insertion, donor rankings,
nearby origins and model seeds. Unreliable or unsupported cases explicitly
abstain. Each wheel/horizon score, signed change and raw perturbed forecast is
saved. Temporal splices are model diagnostics and can violate physical equations.

R028 exhaustively searches55 coupled speed/throttle scenarios. It updates motion
features and recomputes all four past energy proxies, preserving categories,
brake and timing. Source/candidate constraints include unprojected wheel loads,
coupled kinematics, bounded inputs and training-only marginal support. It seeks
a10% (at least.01kJ) forecast-mean decrease, minimizes the declared finite-catalogue
cost and verifies every emitted success independently. The primary XGBoost result
also requires one shared scenario to cross each saved seed's own target.

"Feasible" means within these declared **kinematic/proxy and marginal-support
constraints**. Actual actuator, friction-circle, complete track path, thermal,
race-control and causal intervention feasibility remain **UNKNOWN**. This is a
retrospective model what-if, not an executable driving or strategy recommendation.
No CausalImpact/VSC causal-effect replication or production promotion is claimed.

The original fitted parameters/scalers remain unchanged. Linear/ridge equations
and neural weights are evaluated in float64 after frozen float32 normalization
to remove micro-kJ batch-size rounding. Original R025/R026 results remain intact;
the maximum historical forecast difference is disclosed for each model. A
ten-checkpoint real-data numerical preflight and independent weight reload verify
the new adapter at the unchanged numerical tolerance.

## Run on the preserved public inputs

From the checkout, with the existing environment and frozen R025/R026 artifacts:

```powershell
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
python research/scripts/check_forecast_explanation_numerics.py --reference .cache/tyre-forecast-research-20261012 --evaluation .cache/r026-track-generalization-research-20261013 --cohort docs/verification/forecast-explanation-cohort.json --output .cache/explanation-numerics-new.json
python -m apexsim.cli forecast-explanation-study --reference .cache/tyre-forecast-research-20261012 --evaluation .cache/r026-track-generalization-research-20261013 --cohort docs/verification/forecast-explanation-cohort.json --output .cache/explanation-study-new
python -m apexsim.cli verify-forecast-explanation-study .cache/explanation-study-new
python -m apexsim.cli audit-forecast-explanation-study .cache/explanation-study-new
```

Each output must be new. The run copies complete sealed source inventories,
weights, windows, cohort and protocol documents, so replay works after relocation
without the original cache paths. `summary.json` records the decision;
`results.json` contains per-case explanations, rejected candidates, successes and
abstentions; per-model NPZ files contain raw predictions. Zero values for rejected
candidate slots are explicit storage placeholders, never predictions or candidates
eligible for selection. The signed/raw/projected distinction is retained.

Bulk source windows, weights and run outputs remain ignored locally, following
R025/R026's storage policy. Full public replay needs those preserved frozen runs;
Git contains source, compact acceptance evidence, all cohort keys and inventory
seals. A newly refitted run cannot silently replace a pinned public reference.

## Fresh-checkout simulated execution

After installing `./apex_engine[dev,data-contracts,optimization,forecasting]`:

```powershell
python -m apexsim.cli tyre-forecast-smoke --output .cache/explanation-ref-smoke
python -m apexsim.cli track-generalization-smoke --reference .cache/explanation-ref-smoke --output .cache/explanation-eval-smoke
python -m apexsim.cli freeze-forecast-explanation-cohort --reference .cache/explanation-ref-smoke --evaluation .cache/explanation-eval-smoke --profile smoke --output .cache/explanation-cohort-smoke.json
python -m apexsim.cli forecast-explanation-study --reference .cache/explanation-ref-smoke --evaluation .cache/explanation-eval-smoke --cohort .cache/explanation-cohort-smoke.json --output .cache/explanation-study-smoke
python -m apexsim.cli verify-forecast-explanation-study .cache/explanation-study-smoke
python -m apexsim.cli audit-forecast-explanation-study .cache/explanation-study-smoke
```

The older forecasting smoke fixture is deliberately not a physical proxy
generator. Its inconsistent histories are rejected and its two sequences per
identity do not meet the eight-sequence donor requirement. Synthetic hand fixtures
separately exercise successful physical/scenario and faithful-explanation cases.
Smoke is execution-only and cannot be resealed into public acceptance. Both CI
Python versions exercise the complete interface, replay and independent audit.
