# Experiment Playbook

## Experiment template

```text
ID:
Question:
Hypothesis:
Frozen dataset/split:
Baseline:
Change under test:
Metrics and horizon:
Physical checks:
Expected failure modes:
Result:
Decision:
Artifacts:
```

## Highest-value early experiments

### E01 — Is curvature causal?

Shuffle curvature within sessions and compare matched rollout error. A model that does not degrade may be ignoring track geometry or leaking progress.

### E02 — Does recorded control replay work?

Use identical initial state and recorded controls. Compare physics, linear residual and GRU residual over 1, 2, 5 and 10 seconds.

### E03 — Can a simple model win?

Compare persistence, constant acceleration, Ridge, physics and neural models with the same horizon, split and inputs.

### E04 — Cross-track generalization

Hold out an entire circuit. Determine whether failure is track reconstruction, physics parameters, driver policy or neural overfit.

### E05 — Tyre identifiability

Fit degradation with and without fuel/traffic correction. Report how unstable the coefficient is across sessions.

### E06 — Intervention support

Scale throttle/brake by small amounts and verify monotonic response in synthetic data before using historical data.

### E07 — Planner recovery

Create a synthetic race with a known best pit window. Confirm the planner recovers it and that ranking stabilizes with rollout count.

### E08 — Weather transition

Introduce rain and compare slick/intermediate/wet strategies. Check that the result follows explicit grip assumptions and uncertainty, not a hidden label.

### E09 — Dirty-air sensitivity

Vary the assumed maximum downforce loss. Report strategy/rank sensitivity rather than selecting one convenient value.

### E10 — Residual safety

Adversarially force large residual predictions. Confirm bounded correction and invariants prevent impossible states.
