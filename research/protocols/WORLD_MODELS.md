# Protocol — World Models for APEX

## Role
World models estimate residual dynamics, hidden state and branching futures. They do not replace known constraints or regulation logic.

## Model ladder
GRU deterministic baseline → RSSM probabilistic model → controllable/noncontrollable factorization → PlaNet/CEM → Dreamer actor-critic → TD-MPC2-style latent planning.

## Training target
Prefer physics-residual and latent-event prediction over raw-state replacement. Condition on track, car, driver, tyre, weather and race-control context.

## Tests
One-step, open-loop, closed-loop, calibration, OOD detection, intervention consistency, latent probes, feature permutations, planner exploitation and unseen-track transfer.

## Acceptance
Must beat physics-only and GRU baselines on matched horizons while preserving feasibility through projection or constrained decoding.
