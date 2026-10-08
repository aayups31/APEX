# FIENI strategy foundation verification

- Date: 2026-10-08 (America/Toronto)
- Branch: main; direct commits/pushes authorized
- Baseline: 5676efc84af9a1111b1b6254e30fc480707bbc4d
- Scope: R012-R014; research adaptation, not production promotion
- Maturity before/after: R0
- Status: DONE; R012-R014 acceptance gates passed

## A. Current state

The earliest incomplete P0 research rows are R012, R013 and R014. The existing
strategy scaffold conserves resources on its tested fixtures but uses synthetic
lap-time and tyre coefficients. Its beam search is approximate and lacks an
independent exhaustive benchmark. No published MINLP/SAC result has been reproduced.
The pre-edit research demo completed and its rollout was inspected: race time
772.6651075170051 seconds, zero terminal fuel/battery, compound change true.
Tyre ridge RMSE was 0.055471744758730714 on synthetic proxy targets; its existing
ill-conditioning warning is unrelated to the strategy slice.
The full pre-edit suite passed 244 tests with two existing dependency warnings
in 159.13 seconds. Windows async API tests require local loopback permission;
test temporary directories stay in ignored workspace cache.

## B. Scope

Review every numbered equation and used symbol in the frozen FIENI_2025 PDF.
Correct resource feasibility/action-map errors revealed by that review; add
independently hand-calculated fixtures and a bounded exhaustive tiny-race oracle.
Validate a lossless beam mode against enumeration and expose the approximate beam's
limitations. No neural policy, confidential map reconstruction, physics calibration
or production-kernel change belongs to this slice.

## C. Source-of-truth inputs

Master guide sections 7, 9.5, 9.9, 10 and 17; simulator maturity model; FIENI protocol
and replication standard; research backlog R012-R014; fienia_strategy and strategy_env.
The user-supplied 13-page paper is frozen at SHA-256
fc609aa9dcff9179d5e6cba8ce96eb7785f8db45daeef2fc6c4aad32ad133270.
Relevant pages 3-10 are extracted and visually inspected, because extraction
alone misrepresents fractions and piecewise equations.

## D. Implementation plan

1. Publish equation/symbol/unit/parameter-source maps with every omission and deviation.
2. Restore the affine normalized battery mapping; intersect current input/state
   constraints with the next-state backward-reachable resource intervals.
3. Reject unreachable or invalid states rather than depleting resources faster than
   declared per-lap bounds. Record action corrections and tyre-domain clipping.
4. Add decimal hand calculations for normal, inlap, outlap and consecutive-pit cases,
   projection boundaries, resets and compound legality.
5. Add independently enumerated tiny-race search with a hard preflight budget.
   Preserve the existing beam interface while adding exact future-state dominance.
6. Execute artifact-producing comparisons, targeted/full regression and GitHub checks.

## E. Stopping gate

R012 needs a complete reviewed equation map tied to the frozen paper and code.
R013 needs checked decimal fixtures matching within 1e-9, including bounds/signs/resets.
R014 needs exhaustive finite-grid optima and agreement with unpruned lossless beam
on declared tiny cases; truncated search must never claim exactness or return an
illegal finish as feasible. Report total candidates, feasible counts, race-time
regret, resource legality and search budget. No fitting/evaluation data is used:
all fixtures and search cases are explicitly synthetic. Full tests and lint must
pass before DONE.

## F. Risks and deviations

The paper's Eq. 59 prints a positive recharge limit as a depletion capacity;
using the magnitude of the negative deployment limit is a documented correction.
Backward-reachable bounds must refer to laps remaining after the current action.
The starter's normalized battery map is piecewise rather than the affine Eq. 56.
Its terminal projection can violate input bounds; its coarse beam buckets omit fuel
and outlap state. These errors need tests. Synthetic coefficients, wear saturation,
boolean compound-change state, absent battery-dependent lap maps, omitted MINLP/SAC
and terminal reward penalties remain declared adaptation choices.

## G. Execution and evidence

Implementation checkpoint: 31 targeted tests passed in 22.55 seconds. Ruff and
Airflow wrapper compilation passed. The fresh-process network-guarded acceptance
CLI saved .cache/fieni-foundation-20261008 with zero network attempts.
Five inspected hand fixtures have maximum absolute error 1.4210854715202004e-14.
The single-energy grid exhausts 4 sequences (2 legal), with optimum
304.778138338125 seconds; the asymmetric projected grid exhausts 256 (128 legal),
with optimum 304.766938338125 seconds. Lossless wide beam agrees exactly on both.
Width-one beams discard all legal candidates and explicitly abstain; neither claims
an optimum. Saved exact actions replay to the same legal final states.

The updated research demo also completes: 770.9385021735404 seconds with zero
residual energy and a compound change. The changed synthetic result reflects the
corrected search state grouping and resource feasibility, not better real-race
accuracy. Synthetic tyre forecasting metrics are unchanged. Every inspected reference
allocation satisfies the declared fuel range 77.4..94.6 MJ/lap and battery delta
range -1.25..0.75 MJ/lap; race time increases monotonically.

The full local suite passed **272 tests**, with two existing dependency warnings,
in 162.76 seconds. This is 28 added tests over the verified baseline. Ruff,
Airflow compilation and whitespace checks passed. The implementation checkpoint
d2ba1a43d7f4a12127457d84bc1a677da33980b7 was pushed directly to main.
GitHub Actions [run 37842648078](https://github.com/aayups31/APEX/actions/runs/37842648078)
passed both Python 3.11 and 3.12 jobs, including tests, lint, Airflow compilation and
public-data demo verification.

[Machine-readable evidence](fieni-foundation-evidence.json) records input/code/output
hashes, baseline/new metrics, fixture errors, enumerated/feasible sequence counts,
pruning/abstention evidence, tests and CI. The acceptance summary is
f10cc276b1b2b0ed88172c7a44ba624d0002eb6302c40501a6fcbde0d233e812.

R012 is complete with 70 reviewed equation entries and parameter/symbol units.
R013 is complete with five frozen hand transitions passing the 1e-9 gate.
R014 is complete with two exhaustive tiny projected grids, exact wide-beam agreement
and explicit narrow-beam abstention. These are research adaptation gates, not
published-result replication or production promotion. Research backlog: 14/73 DONE.
The separate 66-task build backlog remains 13/66 DONE, 53 remaining.

Next earliest research dependency: **R015**, a smooth CasADi lap-map surrogate with
gradient and bound checks. The clipped tyre map must not be assumed smooth.
R016 then establishes a matched solver adapter before policy training is compared
against a stronger benchmark. Public lap filtering, track reconstruction and an
untouched multi-event corpus remain separate data/physics prerequisites. Global
maturity remains R0.
