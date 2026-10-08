# R016 strategy solver verification

- Date: 2026-10-08; branch main; baseline 349f51a
- Scope: R016 documented open-source solver adapter
- Status: DONE (component gate); global maturity before/after R0

## A. Current state

R012-R015 supply equation review, hand fixtures, exact finite-grid enumeration,
and tested smooth CasADi lap maps. The last implementation CI passed on Python
3.11/3.12. The fresh baseline passed 316 tests (two existing warnings, 167.24 s).
A local CasADi 3.7.2/IPOPT
one-variable smoke solve returned Solve_Succeeded at x=1.9999999989968953.
No matched continuous strategy solver or trained SAC policy exists yet.

## B. Proposed scope

R016: enumerate bounded discrete schedules and solve continuous fuel/battery
allocation via IPOPT on the R015 objective. Use direct shooting with unclipped
wear/resource equations and explicit domains, reachability and terminal bounds.
Validate solutions independently and replay through the existing starter.
No production replacement, full-race MINLP certification, policy training,
fitted car data or maturity promotion is included.

## C. Source-of-truth inputs

Master guide sections 7, 10, 11, 15-17; FIENI equation review and protocol;
PaperStrategyModel resource/wear/mode semantics; SmoothLapMap units and error
bound. Official CasADi nonlinear-programming documentation was inspected:
https://web.casadi.org/docs/#nonlinear-programming . Numerical constants are
declared synthetic priors or solver tolerances. No training/evaluation data is used.

## D. Implementation plan

Add strategy_solver.py: fixed-schedule CasADi graphs, independent scalar replay,
deterministic feasible energy starts, IPOPT adapter, status/residual diagnostics,
budget checks and abstention. Inputs are per-lap fuel fractions and battery deltas
in MJ; race mass follows remaining fuel/LHV.
After a valid NLP call, retain a better independently feasible starting allocation;
record the selected source and both costs. Starts cannot bypass failed NLP gates.
Pit decisions fix compound/outlap
modes outside the graph. Initial resources match the starter; terminal resources
must both be zero. Wear is never clipped. Last-lap-only pits are unsupported.
Enumerated schedule and horizon budgets must fail before attempting a partial search.

Add a separate tiny continuous reference: independently enumerate resource
polytope vertices for at most three laps. With mass-independent wear and a concave
or linear battery term, each fixed-plan objective is affine in fuel plus concave
in battery, so a minimum occurs at a vertex. Refuse other families; this is not
a general-purpose certificate. Do not share optimizer graph/gradient/start helpers.

Test a hand-calculated linear family (3 laps, 6 kg fuel, 1 MJ battery, both battery
slopes 0.4 s/MJ, wear a=1,b=0,c=0.01). For initial MEDIUM, a pit on lap index 1
to SOFT, and front-loaded fuel [1.1,1,0.9], the optimum is 305.626825 s:
277.5 nominal + 0.3248 mass + 26.5 pit + 1.702025 tyre - 0.4 battery.
Test asymmetric concave battery slopes against the independent vertex reference,
and a coupled six-lap wear case for feasible local performance only.
Add strategy-solver-demo: immutable configurations, solutions, statuses,
resource/objective residuals, regret, runtimes, code/dependency hashes and manifest.
Base imports remain free of CasADi/IPOPT. CI must execute solver acceptance.

## E. Evaluation and stopping gate

Recover declared linear/concave tiny-family optima within 1e-6 s and the linear
fuel allocation within 1e-5. Independent graph/scalar objective parity within
1e-8 s; constraint residuals within 1e-7 in recorded normalized/MJ units;
terminal resources within 1e-7 MJ; legacy replay energy adjustments within
1e-7 MJ. Smooth/piecewise discrepancy no more than laps*R015 bound plus 1e-6 s.
Record statuses and unsuccessful starts/plans; a solver success flag alone is
insufficient. Reject nonfinite/infeasible outputs and never certify a local NLP
as globally optimal. Exhausted schedule budgets return no partial result.
Run targeted failure/domain/gradient/artifact tests, lint, full regression and
Python 3.11/3.12 optimization-enabled CI. Close R016 only after all gates pass.

## F. Risks

Nonconvex objectives, local minima, numerical boundary residuals, wear leaving
the declared box, exponential discrete schedules and dependency/plugin failures.
Restrict this adapter to bounded research horizons and record deterministic starts,
tolerances and runtime. The tiny reference relies on an explicit restricted
concavity argument and numerical vertex tolerances. Synthetic optimum recovery
does not establish real-race strategy quality. Avoid tuning on benchmark data.

## G. Execution order

Baseline/reference inspection; graph/replay and invariant tests; adapter and
independent tiny reference; immutable demo and CI; tested direct-main checkpoint;
full regression/CI; evidence and backlog closure; final direct-main push.

Implementation checkpoint evidence:

- Baseline: 316 tests passed, two existing warnings, 167.24 seconds. R015
  acceptance reran unchanged with summary hash 42c9cd1f5db1e44b768fab38184780d281cacb007b26a962c7fcac45c3555e24.
- Final targeted solver/map suite: 76 passed in 20.88 seconds; lint/compilation passed.
- Restricted Windows verification could not initialize the native IPOPT DLL
  (WIN32 1114/invalid handle). Native-access smoke and tests passed, including
  explicit single-thread limits. No numerical workaround or skipped test was used.
- The initial concave solve returned a stationary point 8.334308745361341e-7 s
  above the independent vertex minimum. Retaining a better independently feasible
  start after successful NLP acceptance corrected this without oracle access or
  tolerance retuning. Candidate provenance remains explicit; global certification
  is still false. Failed calls cannot be accepted through a start.
- Final acceptance: three cases, two matched independent global references,
  all six calls per case accepted; maximum absolute regret 5.684341886080802e-14 s.
- Maximum primal residual 9.992007221626409e-16; terminal resource error
  8.526512829121202e-14 MJ; legacy energy adjustment 7.105427357601002e-14 MJ.
  All intermediate resource/mass/wear/discrete states are compared with legacy
  replay in addition to terminal legality and objective discrepancy.
- Matched baseline improvements: 0.011199999999973898 s (linear),
  0.06119000399792185 s (concave), 0.15087640153501525 s (coupled six-lap).
  The coupled case has no global reference/regret claim.
- Measured solver runtimes on this laptop: 0.1664, 0.1579 and 0.4771 seconds;
  these are measurements, not a policy runtime or hardware-independent promise.
- Final artifacts: .cache/strategy-solver-verified-20261008, summary content hash
  9dc0d6eb7bacc2086ebe2629f8f99d09a51197b47407ad28784d7a0e1db3986c.
  Code hashes/inventory inspected; zero network attempts; base CLI/solver imports
  do not load CasADi. Immutable-output and failed-acceptance tests passed.

Closure evidence:

- Implementation checkpoint 407680cb70f719e101a1da4d1afd70c0a6947037 is pushed to main.
- Full local regression: **348 passed**, two existing dependency deprecation
  warnings, 139.71 seconds. Native DLL and loopback access enabled; OMP, MKL and
  OpenBLAS thread limits were one. No tests skipped for the solver.
- [GitHub Actions run 37850148292](https://github.com/aayups31/APEX/actions/runs/37850148292)
  passed on Python 3.11 and 3.12, including full tests, lint, Airflow compilation,
  public-data artifacts, smooth-map artifacts and matched strategy-solver artifacts.
- R016 is DONE. Research inventory: 16/73 done, 57 remaining. Build inventory:
  13/66 done, 53 remaining. Global maturity remains R0; these inventories do not
  measure real-race accuracy.
- [Machine-readable evidence](strategy-solver-evidence.json) preserves acceptance
  metrics, manifest/source hashes, runtime metadata, candidate provenance,
  reference family/counts and trajectory errors. Maximum legacy mass error was
  1.1368683772161603e-13 kg, fuel error 8.526512829121202e-14 MJ; wear/discrete
  state parity passed. The original strategy core and R015 map remain unchanged.

Next: R017 SAC training/evaluation with matching horizons, state information,
pit windows, control bounds and objective. Keep unclipped wear within the same
domain and account explicitly for smooth versus piecewise costs; evaluate
terminal legality, independent regret and runtime with frozen seeds/configuration.
R018 nominal/disturbed scenarios then precede the planned R1 review. There is
still no published-policy replication, full-race global MINLP guarantee or new
real-race calibration evidence.
