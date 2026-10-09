# R017 synthetic hybrid SAC study

This is an adaptation of the [SAC formulation](https://arxiv.org/abs/1812.05905)
to the reviewed FIENI state/action topology. It trains on a fixed synthetic task.
It does not reproduce confidential paper coefficients or establish real-race skill.

## Frozen task and budgets

Three laps; 6 kg fuel; 1 MJ battery; battery delta [-1,0.5] MJ; mass-independent
wear a=1,b=0,c=0.01 on each dry compound; remaining pace/tyre coefficients are
the recorded starter priors. R015 battery smoothing epsilon=0.01 MJ. Pits are
allowed at lap indices 0 and 1, and a compound change is required before finishing.
Initial training compounds cycle SOFT/MEDIUM/HARD by episode. Each final policy
is evaluated deterministically once on each of these same initial compounds.
These are in-task evaluations, not held-out sessions or generalization tests.

Research seeds: 11,23,37; each receives 12000 environment steps, warmup 512,
batch 128, replay capacity 8192, two hidden layers of width 64 per network,
learning rate 0.0003, fixed temperature alpha=0.01, target mixing 0.005,
maximum gradient norm 10 and undiscounted finite-horizon gamma=1.
Smoke: seed 11, 300 steps, warmup 64 and batch 32; other settings are unchanged.
Smoke validates execution and serialization only. No hyperparameter search,
best-evaluation checkpoint selection, oracle imitation or evaluation replay occurs.

## State, action and equations

The separate learning wrapper normalizes the ten physical state fields using
frozen parameters. Mass is centered before conversion to float32. Smooth elapsed
and last-lap times replace their original counterparts in this wrapper only.
Reward is nominal time minus smooth lap cost. At gamma=1, maximizing its sum
is equivalent to minimizing smooth race time over this fixed horizon.

The energy action is a reparameterized tanh Gaussian with two dimensions; fuel
maps [-1,1] to [0.9,1.1] times nominal allocation. Battery uses the starter's
inverse-sign affine map. The categorical head chooses no pit/SOFT/MEDIUM/HARD.
Energy and pit are factorized conditional on the observation. Pit masks enforce
the allowed window and required change at the final opportunity; reachable
resource projection remains explicit. Stored replay actions are the requested
controls, since the projected transition defines their outcome. Every evaluation
records requested and applied physical actions. Enforced legality is not learned
legality. Unsupported wear clipping is rejected before committing a state.

For sampled energy u and allowed pit choices d:

```text
V(s,u) = sum_d pi(d|s) [min(Q1(s,u,d),Q2(s,u,d)) - alpha log pi(d|s)]
         - alpha log pi(u|s)
y = r + gamma (1-terminal) V_target(s_next,u_next)
critic loss = MSE(Q1,y) + MSE(Q2,y)
actor loss = -mean(V_online(s,u))
target <- (1-tau) target + tau online
```

The continuous density includes the tanh Jacobian, evaluated with a stable
softplus expression. The categorical expectation is exact over four choices.
Actor updates freeze critic parameters while retaining derivatives with respect
to energy. Fixed alpha, hybrid factorization, constraint masks and gamma=1 are
declared adaptations. Local NumPy/Torch generators isolate initialization,
exploration, replay sampling and policy sampling from global random state.

## Comparisons and acceptance

Uniform-energy and greedy feasible-energy rules pit at the first opportunity,
to MEDIUM when initially SOFT and to SOFT otherwise. Compare these rules, the
R016 adapter and independent concave vertex reference using identical parameters,
initial compounds, pit domain and smooth objective. The reference is confined to
this <=3-lap mass-independent-wear concave family. IPOPT remains a local solver.

Every successful rollout replays its applied actions through R016 scalar and
symbolic paths: objective discrepancy <=1e-8 s, physical residual tolerance
1e-7, adapter/reference regret <=1e-6 s. Check original piecewise cost against
the R015 analytic smoothing allowance. Failed policy episodes remain in the
attempt count; legal-only regret aggregates explicitly exclude those failures.
No policy quality threshold is introduced after observing results.

Tests check analytic densities, scalar soft targets, terminal masking, genuine
actor/critic changes, target mixing, replay contracts, seeded reproducibility,
global RNG isolation and checkpoint action parity. R017 completion requires a
full three-seed run, reported regret/runtime, regression checks and Python
3.11/3.12 smoke CI. Completion never implies production promotion: this study
sets promotion_recommended=false even if its in-task scores beat a rule.

## Running and artifacts

Install `apex_engine[dev,optimization]`. Use one CPU thread per numerical library
for comparable laptop runs; save actual thread/library/platform settings.

```powershell
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
.venv/Scripts/python.exe -m apexsim.cli sac-strategy-demo --profile smoke --output .cache/sac-smoke-new
.venv/Scripts/python.exe -m apexsim.cli sac-strategy-demo --profile research --output .cache/sac-research-new
```

Each output root must be new. Save configuration, training traces/reports,
baseline and evaluation trajectories, source hashes, summary and per-seed `.pt`
inference checkpoints. Reload every checkpoint using CPU `weights_only=True`
and check every evaluated action. Write the manifest last; a missing manifest
means incomplete output. Numerical acceptance runs before creating the root;
a serialization failure can leave incomplete output. Existing roots/checkpoints
are never overwritten. Checkpoints intentionally omit optimizer/replay/RNG state
and cannot resume training exactly.

Decision runtime covers the policy or rule call only; planner runtime covers
constructing a complete plan. Training, environment replay and artifact writing
are separate. Do not infer deployment speed from this small task.

Next: R018 nominal/disturbed scenario reconstruction, then a documented R1
review. Global maturity remains R0 until the review's own evidence passes.
