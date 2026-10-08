# Protocol — FIENI_2025 Joint Strategy Model

## Primary claim
A common lap-wise model can support both a mixed-integer optimizer and a fast RL policy for fuel allocation, battery allocation and pit/compound choice.

## Current implementation
`PaperStrategyModel` implements battery, fuel, mass, race time, compound-change, compound, wear and outlap state; affine normalized energy maps; checked backward-reachable projection; surrogate wear/lap-time dynamics; and race legality. `DiscreteStrategyOracle` is an approximate beam benchmark. `ExactStrategyOracle` independently enumerates bounded tiny projected action grids, not the paper's continuous MINLP.

The [reviewed equation map](../equations/FIENI_2025.md) covers all 70 printed
equation numbers with units, symbol-to-code references, source anomalies and omissions.
The [hand fixtures](../fixtures/fieni-hand-transition-v1.json) use frozen synthetic
parameters and absolute 1e-9 tolerances. No published-policy or confidential
lap-map reproduction is claimed, and global maturity is not promoted.

[R015 smooth maps](../equations/SMOOTH_LAP_MAP_V1.md) supply separate synthetic
CasADi values/gradients/Hessians for fixed compounds and modes. Numeric calls
reject extrapolation; symbolic callers must impose explicit box and resource
constraints. The smooth battery term has a declared approximation-error bound.

## Next experiments
Next: establish matched solver benchmarks (R016), then train a policy against
the same validated dynamics (R017) and reconstruct nominal/disturbed scenarios
(R018). R016 must distinguish locally solved continuous NLPs from a certified
global mixed-integer optimum; solver success alone does not certify either
terminal legality or optimality. Recover independently known small-case optima,
replay saved actions and report primal/resource residuals, solver status,
objective/regret and runtime. Compare matching domains and objectives; account
for the R015 smoothing discrepancy when replaying the original piecewise map.
Public tyre fitting requires separated calibration/benchmark events. Disturbance
and runtime comparisons precede any later hybrid planning work.

## Reproducible acceptance

From the repository checkout:

```bash
apexsim strategy-foundation-demo --output .cache/fieni-foundation-new
apexsim smooth-lap-demo --output .cache/smooth-lap-new  # optimization extra
cd apex_engine
pytest -q tests/test_fieni_foundation.py tests/test_research_fienia_strategy.py
```

The output is immutable: fixture errors, exhaustive candidate/feasible counts,
matched wide-beam regret, narrow-beam abstention and source/code hashes are saved.
Optima concern synthetic projected finite grids only. No fitting or test-data tuning
is involved. See [verification evidence](../../docs/verification/fieni-foundation-report.md).
Smooth-map acceptance and limitations are recorded in its separate
[verification report](../../docs/verification/smooth-lap-map-report.md).

## Acceptance
Terminal fuel/battery legality, required compound change, exact small-case agreement, nominal regret, disturbed regret and runtime.
