# R017 SAC strategy training and evaluation

- Date: 2026-10-08; branch main; baseline 87c9876
- Scope: R017; status IN_PROGRESS; global maturity before/after R0

## A. Current state at session start

R012-R016 provide reviewed dynamics, hand fixtures, exact finite-grid and restricted
continuous references, smooth maps and a bounded local optimizer. Fresh regression:
348 passed, two existing dependency warnings, 225.61 seconds. No SAC policy is
trained yet. Existing strategy transitions and environment interfaces are preserved.

## B. Scope

Train a factorized hybrid SAC research policy on the same synthetic FIENI dynamics:
continuous normalized energy controls and categorical pit selection. Compare frozen
deterministic policies with simple matched rules, R016 and the restricted continuous
reference. Report legality, projection frequency, regret and runtime. No production
promotion, confidential-paper replication, real-data training, full-race performance
or global maturity promotion is included.

## C. Sources

Master guide sections 10-13, 15-17; FIENI equation table; PaperStrategyModel/Env;
R015 objective and R016 domain/protocol. SAC papers 1801.01290/1812.05905 and the
authors' OpenAI Spinning Up PyTorch SAC source were inspected. The exact categorical
expectation and action masks are declared adaptations, not copied paper results.
Training data are generated synthetic episodes; no public benchmark session is used.

## D. Implementation

Add a separate learning wrapper: preserve the ten physical observation fields,
normalize using frozen task parameters, and use smooth elapsed/last-lap time.
Reward = nominal_lap_time - smooth_lap_time, with undiscounted finite-horizon
gamma=1; its episode sum differs from negative race time by a fixed constant.
Pit masks impose the R016 window/no-final-pit domain and the real required-change
constraint at its last opportunity. Energy uses the starter's recorded reachable
projection. Legality enforced by these mechanisms is not evidence it was learned.
Reject wear clipping and report requested/applied actions separately.

Implement twin critics, target critics, a reparameterized tanh Gaussian energy
actor and categorical pit head. Use a stable tanh Jacobian correction, exact
expectation over allowed pit choices, fixed positive entropy temperature, replay
and Polyak updates. Local NumPy/Torch generators isolate random state. CPU only;
frozen observation scaling, seeds and library versions are saved. No oracle actions,
imitation, reward retuning or evaluation transitions enter gradient updates.

Pre-register the synthetic task: three laps, 6 kg fuel, 1 MJ battery, delta bounds
[-1,0.5] MJ, mass-independent wear (a=1,b=0,c=0.01), default pace/tyre priors,
pit window indices [0,1]. Train on all three initial dry compounds; evaluate each
once deterministically per frozen policy. This estimates in-task optimization
behavior, not unseen-event generalization. No held-out real-world claim is made.
Research: seeds [11,23,37], 12000 steps each, width 64, batch 128, warmup 512,
replay 8192, learning rate 0.0003, alpha 0.01, target mixing 0.005. Smoke profile:
seed 11, 300 steps, batch 32, warmup 64. No hyperparameter search or best-evaluation
checkpoint selection. Save weights, training traces and separate evaluation rollouts.

Compare uniform-energy early-pit rule, greedy feasible energy early-pit rule,
R016 local adapter and independent concave vertex minimum with identical model,
pit window, initial compound and smooth objective. Compare full trajectory replay
and original piecewise cost with its analytic error allowance.

## E. Gate

Analytic soft-target/actor-loss/tanh-density checks; finite nonzero actor/critic
updates; isolated seeded RNG; reproducible same-runtime weights; illegal/malformed
inputs rejected; masks valid; terminal bootstrap disabled; checkpoint save/load
action parity. Policy and baseline actions replay through R016 with objective
agreement within 1e-8 s and its physical residual tolerances. Independent reference
and adapter agree within 1e-6 s. Regret is measured honestly, with all failed
episodes counted; no performance threshold is changed after observing evaluation.
R017 gate is training plus reported regret/runtime, not superior policy quality.
If no advantage over strong rules is established, retain the policy as research
and set promotion_recommended=false. This fixed-task study cannot establish
held-out advantage regardless of its scores. Immutable artifacts, targeted/full
tests, lint and Python 3.11/3.12 smoke CI must pass before closing R017.

## F. Risks

Small energy cost differences, critic approximation, seed variability, entropy bias,
action-projection plateaus, masks concealing learned legality, model exploitation
and overfitting a tiny synthetic task. Keep all these limitations visible. Training
may be worse than a rule; report that outcome without retuning the benchmark.
Do not equate a trained policy with a calibrated world model or deployed agent.

## G. Order

Baseline; learning wrapper and equation/invariant tests; SAC and checkpoint tests;
immutable smoke artifact run; tested direct-main checkpoint; frozen three-seed
research run; full regression/CI; evidence and backlog closure; final main push.

Implementation checkpoint evidence:

- Targeted SAC equation/environment/training/artifact tests: 31 passed in 37.75 s.
- Repository lint, Airflow wrapper compilation and diff whitespace checks passed.
- Immutable smoke: .cache/sac-smoke-20261008; 300 transitions, 100 completed
  episodes and 236 gradient updates. All three deterministic evaluation episodes
  were legal; every reloaded checkpoint action matched its saved rollout.
- Smoke mean regret was 26.846913838696594 s, maximum 27.446957353086987 s.
  This is an execution check, not adequate learning or promotion evidence.
  Summary hash: 12d295c1b24a4d0d8783e2901aaa71ac2b449fd8c5bf27dfda127d3064d9e5d8.
- A full suite was initially invoked from the repository root; existing tests
  referencing configs/fast.yaml require apex_engine as the working directory.
  The final regression will use the documented engine working directory.
- Full three-seed research training and Python 3.11/3.12 CI remain pending.
  R017 stays IN_PROGRESS until the predeclared completion gate passes.
