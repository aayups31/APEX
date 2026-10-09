# R017 SAC strategy training and evaluation

- Date: 2026-10-08; branch main; baseline 87c9876
- Scope: R017; status DONE; global maturity before/after R0

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

Primary algorithm sources: [original SAC](https://arxiv.org/abs/1801.01290),
[SAC algorithms/applications](https://arxiv.org/abs/1812.05905) and the authors'
[Spinning Up implementation](https://github.com/openai/spinningup/blob/master/spinup/algos/pytorch/sac/sac.py).

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

Evidence at the implementation checkpoint, before full training/CI:

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
- Full three-seed research training and Python 3.11/3.12 CI were pending.
  R017 remained IN_PROGRESS at that checkpoint.

Closure evidence:

- Implementation checkpoint f9fa9d4346ea080b404a1441b1bce66581040725 is pushed
  directly to main. Full local regression: **379 passed**, two existing dependency
  deprecation warnings, 229.89 seconds, from apex_engine with native DLL/loopback
  access and OMP/MKL/OpenBLAS limits of one. The initial root invocation had
  366 passing tests and 13 missing-config failures; no source fix or test skip
  was used to obtain the final passing run.
- [GitHub Actions 37877082528](https://github.com/aayups31/APEX/actions/runs/37877082528)
  passed both Python 3.11/3.12 jobs, including lint, full tests, Airflow compilation,
  public-data, smooth-map, solver and SAC smoke artifact gates.
- Full fixed research study: **36,000 transitions**, **12,000 completed synthetic
  episodes**, **34,464 gradient updates**, seeds 11/23/37. Each seed used 12000
  steps and 4000 episodes. All nine deterministic evaluation attempts were legal;
  zero evaluation transitions entered replay. All saved/reloaded policy actions
  matched, including later-lap states and masks. Final weights were used for every
  seed, without evaluation selection or subsequent tuning.
- Actor/online-critic trainable count: 16,010 per seed; 10,626 additional target
  parameters. CPU training took 291.14/240.08/231.64 seconds, totaling 762.87 s.
  The first seed overlapped regression work; runtimes are observations on this
  machine/load. Neural calls averaged 0.534 ms per lap across 27 calls. The full
  adapter plans took 1.18-2.01 s; these time different operations and establish
  no deployment-speed claim.

Matched mean race-time regret in seconds (three fixed initial compounds):

| Strategy | Mean regret | Maximum regret |
|---|---:|---:|
| Uniform-energy early-pit rule | 0.344263 | 0.910408 |
| Greedy feasible-energy early-pit rule | 0.283073 | 0.849218 |
| R016 local adapter | approximately 0 | approximately 0 |
| SAC seed 11 | 0.335726 | 0.899468 |
| SAC seed 23 | 0.893098 | 1.799218 |
| SAC seed 37 | 0.872422 | 1.753235 |
| All SAC seeds/cases | 0.700415 | 1.799218 |

The policy improved substantially over the short smoke run, but every seed's
mean regret exceeded the greedy rule. Across the nine fixed cases, descriptive
regret standard deviation was 0.683125 s; this is not a confidence interval or
held-out estimate. Compound breakdowns and all rollouts are retained in
[machine-readable evidence](sac-strategy-evidence.json).

Observed failure pattern: every MEDIUM-start policy delayed the pit to index 1;
seeds 23/37 also delayed HARD-start stops. Those extra laps on slower compounds
account for most regret against the matched reference. SOFT starts instead benefit
from delaying the required switch: their regrets were 0.05005/0.00891/0.00953 s.
The legality mask forces a change at the last opportunity, so legal completion
does not demonstrate that the policy learned that rule or selected a good stop.
Training projections affected 67.13/70.71/70.51% of transitions; requested/applied
actions and magnitudes remain visible. These observations justify retaining the
policies in research, not changing the frozen task to make them look better.

- Maximum scalar/symbolic objective discrepancy: 5.684341886080802e-14 s;
  maximum primal residual: 1.652424966883954e-16. Maximum original-versus-smooth
  discrepancy: 0.0014875209552656088 s, below the declared 0.0015 s allowance.
- Immutable research output: .cache/sac-research-20261008; three inference `.pt`
  files plus configuration, reports, traces, comparisons and final manifest.
  Summary content hash: 6077dac5a027c88985ec3961ae44539937ae3442141f08fede12ff32e8fc5414.
  Manifest content hash: 7197368783a3b0dfb8e3c6967ee9d2da8692a66f221e4a5ca764683551550042.
  Every file's byte count/hash and summary/manifest payload hashes were verified;
  source hashes match the tested checkpoint. Weights stay in the local ignored
  output; their hashes, metrics and full evaluation rollouts are versioned here.
- R017 is DONE because the predeclared training/regret/runtime gate passed.
  Added policy value on held-out tasks remains INCONCLUSIVE; promotion is false.
  No confidential-paper replication, held-out event result, calibrated world model
  or production strategy capability is claimed. The original strategy core,
  starter environment and R015 maps remain unchanged. Reverting the implementation
  checkpoint rolls back this isolated extension without changing those modules.
- Research inventory: **17/73 done**, 56 remaining. Build inventory: **13/66 done**,
  53 remaining. Global maturity remains **R0**.

Next: R018 nominal/disturbed scenario reconstruction and directional comparisons,
using frozen policies plus matched rules/optimizer. Preserve the distinction
between synthetic directional evidence and published magnitude replication.
Then perform the planned R1 review; promotion requires its own evidence.
