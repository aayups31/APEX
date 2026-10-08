# R016 bounded continuous strategy solver

Classification: **ADAPTATION**, synthetic **PRIOR** coefficients, global maturity
**R0**. This is a documented open-source solver adapter, not replication of the
paper's confidential maps or global MINLP results. Dependencies are the
[FIENI equation review](../equations/FIENI_2025.md) and
[R015 smooth maps](../equations/SMOOTH_LAP_MAP_V1.md).

`EnumeratedStrategySolver` enumerates every allowed pit/compound schedule before
solving its continuous allocation with the CasADi IPOPT plugin. Each problem
uses fuel fractions followed by battery deltas (MJ), with mass eliminated through
remaining fuel/LHV and wear propagated without clipping. Domain/resource
constraints include backward-reachable fuel, bounded/reachable battery, wear
`[0,1.25]` and zero terminal fuel/battery. Pit/compound modes are fixed per graph.
The final lap cannot introduce a pit-only compound change. A pit on lap index
`i` applies to the next lap, matching the starter.

IPOPT solves bounded nonlinear programs using symbolic derivatives; its
interface is described in the [official CasADi documentation](https://web.casadi.org/docs/#nonlinear-programming).
The adapter always reports `global_optimality_certified=false`. Complete discrete
enumeration does not make a nonconvex continuous solve global. It accepts an NLP
call only after successful status, finite objective and independent scalar replay
agree. Legacy replay must finish legally with no wear clipping and at most
`1e-7 MJ` numerical action adjustments. Objective parity is checked to `1e-8 s`;
smooth/piecewise differences must fit the per-lap R015 bound plus `1e-6 s`.

Three deterministic backward-reachable starts use uniform allocation and opposing
fuel front/back loading with alternating battery-bound choices. After accepting
an NLP call, a better independently feasible starting allocation is retained as
the incumbent. Diagnostics record both objective values and whether `nlp` or
`feasible_start` was selected. A failed or invalid NLP call cannot bypass its
acceptance gate through a start. All invalid calls yield `SolverAbstention` with
diagnostics; numerical failure is not a proof of infeasibility. Partial plan
failures remain explicit, even if another plan produces a usable local candidate.

`SolverSettings` records iteration/tolerance budgets. At most eight laps are
supported; raw pit-sequence budgets are checked before any solver construction.
Exceeding a budget returns no partial result. The default whole-horizon pit
enumeration can therefore reject a long horizon; specify an appropriate window.
This is a bounded research path, not a full 57-lap race optimizer.

## Independent reference family

`tiny_continuous_reference` supports at most three laps with mass-independent
wear (`b=0`) and recharge slope no larger than deployment slope. For each fixed
plan, wear/compound/mode costs are then independent of continuous controls;
mass and fuel costs are affine in fuel. The smooth battery Hessian is nonpositive,
so total battery cost is concave. Energy constraints form bounded polytopes:
fuel ratios in `[0.9,1.1]` summing to N; battery deltas bounded per lap, summing to
negative initial capacity, with every prefix state in `[0,capacity]`.

A concave function on a bounded polytope has a minimum at a vertex. The reference
independently enumerates active-constraint intersections (terminal equality plus
N-1 independent active inequalities), rejects infeasible points, deduplicates them,
and evaluates all vertex pairs and legal discrete plans with scalar equations.
Terminal conservation and per-lap bounds imply backward reachability. Its numeric
feasibility tolerance is `1e-9`; it does not use optimizer graphs, gradients,
starts or projected transitions. Wear must stay unclipped throughout the declared
family. Unsupported coupled/nonconcave families are refused, not certified.

## Executable gate

```powershell
python -m pip install -e './apex_engine[optimization]'
python -m apexsim.cli strategy-solver-demo --output .cache/strategy-solver-new
```

The immutable run saves full configurations, baseline and optimized actions/states,
reference vertex counts, solver statuses, candidate provenance, residuals, regret,
runtime and implementation/dependency hashes. A final inventory manifest seals the
JSON files. Runtime is measured and is not bitwise deterministic. Numerics are
checked with fixed tolerances and deterministic starts. Failed acceptance creates
no output root; an existing directory is refused. Base imports do not load CasADi.
CI installs the optimization extra and runs the full gate on Python 3.11/3.12
with OMP/MKL/OpenBLAS thread limits of one. Restricted Windows environments may
deny native DLL initialization; run verification with native library access.

Cases: the hand optimum **305.626825 s**, asymmetric battery allocation against
the concave vertex reference, and coupled six-lap wear against a matched feasible
baseline. The coupled case has **no** global reference/regret claim. See
[verification report](../../docs/verification/strategy-solver-report.md).
R017 policy training must compare matching horizons, state information, control
domains and objectives; reported piecewise-policy regret must account for smoothing.
