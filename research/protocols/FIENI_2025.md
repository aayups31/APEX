# Protocol — FIENI_2025 Joint Strategy Model

## Primary claim
A common lap-wise model can support both a mixed-integer optimizer and a fast RL policy for fuel allocation, battery allocation and pit/compound choice.

## Current implementation
`PaperStrategyModel` implements battery, fuel, mass, race time, compound-change, compound, wear and outlap state; normalized fuel/battery plus discrete pit actions; feasibility projection; wear/lap-time dynamics; and race legality. `DiscreteStrategyOracle` supplies a transparent small-case benchmark, not the paper’s MINLP.

## Next experiments
1. Hand-check every equation and unit. 2. Fit wear/lap corrections to public stint data. 3. Implement CasADi continuous maps. 4. Add exact enumeration/DP for tiny races. 5. Implement MINLP when a compatible solver is available. 6. Train SAC with identical dynamics. 7. Compare race-time regret and disturbance response. 8. Add RL-discrete + MPC-continuous hybrid.

## Acceptance
Terminal fuel/battery legality, required compound change, exact small-case agreement, nominal regret, disturbed regret and runtime.
