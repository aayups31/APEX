# Smooth lap-map verification

- Date: 2026-10-08 (America/Toronto)
- Branch: main; direct checkpoints authorized
- Baseline: a2f47d1
- Scope: R015, research continuous lap-map surrogate
- Maturity before/after: R0
- Status: IN_PROGRESS

## A. Current state

R012-R014 provide the reviewed FIENI equation map, frozen hand calculations and
an exact tiny projected-grid oracle. R015 is the earliest incomplete P0 research
task. The starter has a battery slope discontinuity at zero and clips tyre wear;
it must not be treated as a twice-differentiable optimization map. Existing
production dynamics and strategy transitions remain the baseline.
The foundation reference was rerun at .cache/smooth-baseline-foundation-20261008:
five fixtures passed with maximum error 1.4210854715202004e-14, both exhaustive
comparisons had zero wide-beam regret, and saved source/code hashes were inspected.

## B. Scope

Implement a separate CasADi continuous map for fixed dry compound and fixed lap
mode. Preserve the starter's declared synthetic fuel/mass/tyre terms on the
supported domain, smoothly approximate its battery term, expose values,
Jacobians/Hessians and explicit box constraints, and reject unsupported numeric
inputs. Produce immutable acceptance artifacts. No solver, trained policy,
production replacement, public calibration or published-map reproduction is included.

## C. Source-of-truth inputs

Master guide sections 7, 10, 11 and 17; FIENI equation review (27-30, 42-43, 47);
R015 gradient/bound acceptance; PaperStrategyParameters and tyre coefficients;
the frozen synthetic hand fixtures. CasADi's official symbolic/calculus/function
documentation was inspected. CasADi is an optional optimization dependency;
the installed base environment uses uv and initially had neither pip nor CasADi.

## D. Implementation plan

Use continuous coordinates [fuel_MJ, battery_delta_MJ, mass_kg, wear].
Fixed mode/compound stay outside differentiation. Evaluate the tyre polynomial
without clipping on the declared wear interval; supply the interval as constraints.
For battery delta d, replace the piecewise term with

    B(d) = 0.5*(k_deploy+k_recharge)*d
         + 0.5*(k_recharge-k_deploy)*(sqrt(d*d+eps*eps)-eps).

eps is a named positive prior in MJ. B(0)=0, and the absolute discrepancy from
the starter is at most 0.5*abs(k_recharge-k_deploy)*eps seconds.
Reject invalid parameter domains and nonfinite/out-of-domain numeric evaluations.
Symbolic callers must apply exposed box bounds and separate resource constraints.
Compare CasADi derivatives with independent closed forms and finite differences,
including zero and both battery signs. Exercise every compound/mode and bounds.

## E. Stopping gate

Within the declared synthetic domain: value parity with an independent NumPy
implementation within 1e-10 seconds; battery approximation discrepancy no larger
than its analytic bound plus 1e-10; analytic derivative agreement within 1e-10;
finite-difference gradient absolute tolerance 1e-6 plus relative 1e-5, and Hessian
tolerance 1e-5 plus relative 1e-4. Derivatives must remain finite at zero and domain
edges; Hessians must be symmetric. Test expected fuel, mass, battery and tyre
directions; reject unsupported inputs without clipping. Optional-dependency
absence must not break base CLI imports. Full suite, lint and Python 3.11/3.12
optimization-enabled CI must pass. No calibration or held-out data is used.

## F. Risks

Smoothing creates high curvature for very small eps; it does not calibrate car
physics. Box membership does not establish resource feasibility of a race state.
Removing clipping means symbolic callers must enforce domain constraints.
Fixed mode/compound maps are not a continuous pit-decision formulation.
Current-battery lap-map dependence and confidential fitted maps remain absent.
Invalid coefficients can destroy monotonicity or positive lap-time bounds and
must fail construction. A component gate alone does not promote global maturity.

## G. Execution order and evidence

Baseline tests/reference inspection; smooth map with explicit constraints;
independent derivative/bound tests; artifact-producing acceptance command;
targeted checks and main checkpoint; full regression/CI; evidence/backlog closure
and final main push. Completion evidence is pending.

Implementation checkpoint:

- Baseline: 272 tests passed, two existing warnings, 117.92 seconds.
- Targeted R015 suite: 44 passed; lint and byte compilation passed.
- Base CLI import left CasADi unloaded; absence gives an actionable optional-extra error.
- Pace-only parity against the existing starter was checked at all compound/mode
  corners and battery join points. These are not feasible full-race trajectories.
- Offline acceptance: 12 maps, 228 reference checks, 60 finite-difference checks,
  eight rejected box violations, zero network attempts.
- Maximum value error: 2.842170943040401e-14 s. Maximum discrepancy from the
  piecewise prior: 0.0004980000320244926 s, below the 0.0005 s analytic bound.
- Maximum analytic gradient/Hessian errors: 8.881784197001252e-16 and
  3.552713678800501e-15. Finite-difference errors: 4.913199513900679e-9 and
  2.500277229700032e-8; all declared absolute/relative tolerances passed.
- Artifacts: .cache/smooth-lap-20261008, summary content hash
  a6735538f92c29fd223d3a6467fc78b15fa05243ab4d119eddd93a6bb5cbad18.

Full regression and optimization-enabled CI remain the closure gate.
