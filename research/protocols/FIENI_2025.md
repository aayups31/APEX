# Protocol — FIENI_2025 Joint Strategy Model

## Primary claim
A common lap-wise model can support both a mixed-integer optimizer and a fast RL policy for fuel allocation, battery allocation and pit/compound choice.

## Current implementation
`PaperStrategyModel` implements battery, fuel, mass, race time, compound-change, compound, wear and outlap state; affine normalized energy maps; checked backward-reachable projection; surrogate wear/lap-time dynamics; and race legality. `DiscreteStrategyOracle` is an approximate beam benchmark. `ExactStrategyOracle` independently enumerates bounded tiny projected action grids, not the paper's continuous MINLP.

The [reviewed equation map](../equations/FIENI_2025.md) covers all 70 printed
equation numbers with units, symbol-to-code references, source anomalies and omissions.
The [hand fixtures](../fixtures/fieni-hand-transition-v1.json) use frozen synthetic
parameters and absolute 1e-9 tolerances. No published policy, nonlinear lap map or
global simulator maturity promotion is claimed.

## Next experiments
Complete equation/fixture/exhaustive-grid acceptance before continuous maps.
Next: implement and validate a smooth CasADi surrogate (R015), establish matched
solver benchmarks (R016), then train a policy against the same validated dynamics.
Public tyre fitting requires separated calibration/benchmark events. Disturbance
and runtime comparisons precede any later hybrid planning work.

## Reproducible acceptance

From the repository checkout:

```bash
apexsim strategy-foundation-demo --output .cache/fieni-foundation-new
cd apex_engine
pytest -q tests/test_fieni_foundation.py tests/test_research_fienia_strategy.py
```

The output is immutable: fixture errors, exhaustive candidate/feasible counts,
matched wide-beam regret, narrow-beam abstention and source/code hashes are saved.
Optima concern synthetic projected finite grids only. No fitting or test-data tuning
is involved. See [verification evidence](../../docs/verification/fieni-foundation-report.md).

## Acceptance
Terminal fuel/battery legality, required compound change, exact small-case agreement, nominal regret, disturbed regret and runtime.
