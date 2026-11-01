# R036 conditional imitation driver

Accepted conditional research component (R036 DONE,2026-11-01): every gate in the
[preregistered protocol](../../research/protocols/IMITATION_DRIVER.md) passes.
The [verification report](../verification/imitation-driver-report.md) records all
eight final cases passing,44 exactly regenerated comparator/refinement runs and
713 passing tests locally and on Python3.11/3.12 CI. Nominal tracking RMSE improves
23.6452% over R035; worst nominal peak error rises from.326161m to.383115m.
Production and formal maturity remain unchanged. [Source contract](../data/imitation-driver.md).

## What is learned

A compact supervised policy learns a steering correction from a simulated expert.
The expert augments frozen R035 steering with known-map curvature preview; its
preview interval is selected using2024 Bahrain validation only. The student then
imitates that correction using current simulated state, previous applied steering
and the supplied map. It cannot see future measured speed/control, event IDs,
absolute XY/station as features, or expert answers during deployment.

Degree1 ridge has9 coefficients and degree2 ridge45, including an unpenalized bias.
Eight training means and eight scales are stored separately from those coefficients.
Both penalty candidates {1e-8,1e-4} genuinely fit generated labels. Training-only
weighted means/scales prevent validation/test normalization leakage. Event,
driver, lap-condition, disturbance and collection-round weights are balanced.
The initial behavior-cloning learner is executed on training conditions, its visited
states receive expert labels, and one aggregated checkpoint is fitted. Validation
chooses the frozen final checkpoint. The expert remains a separate comparator:
student improvement over R035 may come from inheriting a better expert.

Longitudinal control, pace, vehicle and actuators remain transparent and shared.
Learned corrections are limited to +/-.2rad with every intervention recorded;
physical road-wheel, steering-rate, drive/brake and friction limits still apply.
Axle capacity is recomputed at the actual applied steering. Six chassis states
evolve through R032 integration, with no path constraint, resets or state clipping.

## Truth and evaluation scope

Demonstrations and steering labels are SIMULATED, vehicle parameters PRIOR, map
geometry RECONSTRUCTED, initial scalar source speed parsed-source and initial body
lateral velocity/yaw rate zero PRIOR. Real steering/body lateral measurements are
UNKNOWN. This is conditional expert imitation, not recovered human driving style
or calibrated F1 pace. Existing R035 source-time/speed discrepancies remain.

Whole events split2023 Bahrain/Monza training,2024 Bahrain validation and2024 Monza
test. Known maps and development events are reused; nine permanently reserved
benchmark events are untouched. Four test source conditions each have nominal and
signed small-disturbance cases, with identical information and limits for every
comparator. Broader multi-lap drift and OOD/fallback belong to R037/R038.

## Reproduction

```powershell
apexsim prepare-imitation-dataset --teacher .cache/r035-public-20261031 --output .cache/r036-dataset-NEW
apexsim fit-imitation-driver --dataset .cache/r036-dataset-NEW --output .cache/r036-development-NEW
apexsim verify-imitation-development .cache/r036-development-NEW --receipt .cache/r036-development-replay-NEW.json
# Freeze/push the expert choice and genuine model weights before test evaluation.
apexsim evaluate-imitation-driver --development .cache/r036-development-NEW --verification .cache/r036-development-replay-NEW.json --output .cache/r036-evaluation-NEW
apexsim verify-imitation-driver .cache/r036-evaluation-NEW --receipt .cache/r036-evaluation-replay-NEW.json
```

All destinations must be fresh. The simulated command
`apexsim imitation-driver-smoke --output .cache/r036-smoke-NEW` exercises the whole
pipeline without public-task eligibility. Portable JSON checkpoints contain no
executable pickle. Exact inventories and numerical replay are separate checks.

Independent scalar observations/expert labels, pivoted-QR ridge, complete dynamic
development replay and independent held-action bisection/DOP853 lap replay provide
separate checks. The final verifier regenerates every test comparator/refinement,
rechecks training equations/selection after relocation, and binds the pre-test
development-dynamics replay receipt to the exact frozen development package.

## Limits

A simple analytic target is intentionally easy to represent with quadratic
features. This demonstrates controlled conditional imitation infrastructure, not
new driving knowledge or superiority over the expert. The coefficients are policy
weights, not identifiable physical parameters. Few reused development conditions,
generic grip/aero, supplied offline localization/map, fixed pace and absent human
action measurements limit interpretation. A bounded correction is not an OOD
detector or validated fallback. Production use requires later evidence gates.
