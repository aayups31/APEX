# R1 equation-foundation gate review

Date: 2026-10-09. Reviewed baseline: a4d93bb092999a3e618320fc8512ab7a2999d40e.

## A. Current state

R001-R018 are DONE. Research inventory is 18/73; build inventory is 13/66.
Before review, the project research foundation is R0. The production simulator
also remains R0. There are no outstanding R1 backlog rows. Existing untracked
artifacts are preserved and are not inputs to this review.

Fresh baseline: 418 passed, two existing dependency warnings, 149.23 s, at
`.cache/r1-review-baseline-20261009`. Repository Ruff passes. Fresh foundation
acceptance at `.cache/r1-review-foundation-20261009` reproduces the recorded
summary hash f10cc276b1b2b0ed88172c7a44ba624d0002eb6302c40501a6fcbde0d233e812.
Fresh frozen-policy scenarios at `.cache/r1-review-scenarios-20261009` pass
105/105 episodes, all eight gates and no-training/input-immutability checks.

## B. Scope

Review the R1 criterion: paper equations execute independently, with equation
maps, unit tests and published-case reconstruction where possible. Decide the
research foundation's maturity within the reviewed domain. This is an evidence
review, not production component promotion, paper-magnitude replication,
historical-data calibration or a validated adaptive race agent.

## C. Source-of-truth inputs

Master guide sections 7, 10-13 and 15-17; the simulator maturity model and
replication standard; R001-R018 backlog rows; FIENI equation/unit map and hand
fixtures; R015-R018 protocols; foundation, smooth-map, solver, SAC and scenario
verification reports and their machine evidence. The supplied frozen paper is
identified by SHA-256, not by an assumed latest online revision.

## D. Review method

Audit nested content digests, current implementation hashes against recorded
acceptance snapshots, fresh output file inventories/hashes, equation/fixture
lineage and deterministic scenario trajectories. Reuse the successful recorded
R015-R018 comparisons rather than retraining or selecting better policies.
Inspect numerical outcomes and limitations; preserve original schema versions
and historical maturity labels. Record a scoped status separately from runtime
kernel status, without moving research code into `sim_core`.

## E. Decision gate

All three R1 requirements must have direct evidence, the fresh baseline and
reference commands must pass, and source/input lineage must be intact. A missing
equation map, unexplained source mismatch, invalid fixture, failed test or missing
scenario reconstruction refuses promotion. Unknown private coefficients prevent
published-magnitude replication; they do not prevent the explicitly permitted
equation-level adaptation gate when omissions and priors remain documented.

| Gate | Evidence | Decision |
|---|---|---|
| Retain R0 invariants/reproducibility | Fresh 418-test baseline; existing seed stability, physical invariant and artifact tests | PASS |
| Equation and unit map | Frozen FIENI entries 1-70, code locations, units, corrections and omissions | PASS |
| Independent numerical tests | Five decimal hand transitions, max error 1.4210854715202004e-14; two exhaustive grids, zero wide-beam regret | PASS |
| Smooth objective fidelity | R015 twelve maps, analytic/finite-difference gradients and Hessians, explicit smoothing bound | PASS within synthetic domain |
| Matched solver/policy comparison | R016 restricted-family references; R017 final three-seed SAC regret, projections and inference parity | PASS as comparison evidence; policy superiority not established |
| Published-case reconstruction where possible | R018 source catalog records printed schedules, gaps and runtime bounds; unknown maps/resources/dose explicit | PASS for reconstruction; numeric replication INCONCLUSIVE |
| Causal directional analogue | R018 five cases, three compounds, 105 legal episodes; matched-state scores and independent replay | PASS, DIRECTIONAL_MATCH |
| Source and artifact lineage | 23 current-source checks, 18 embedded/fresh content digests, fresh inventories and 105 exactly repeated trajectories | PASS |

## F. Risks and limits

The equation map is an adaptation with declared omissions and corrections, not
all printed equations implemented unchanged. Synthetic lap maps are priors;
the observed-state oracle has a restricted <=3-remaining-lap concave family.
Local IPOPT success does not certify global mixed-integer optimality. SAC has
not surpassed rule baselines or learned legality and showed no pit-choice
adaptation in the disturbance study. Todd tyre energy remains a proxy protocol;
other paper families remain at their recorded starter/protocol stages. The
R1 decision cannot promote these components or establish their paper claims.

## G. Execution order and stopping point

Baseline and fresh references; inspect outputs; check hashes and repeatability;
record decision and machine evidence; publish scoped project status; commit and
push to main. Next implementation slice: R019 immutable multi-event manifests,
then R020 permanent untouched benchmark selection, before any R2 fitting.

## H. Final decision

**PASS_SCOPED_R1_EQUATION_FOUNDATION.** The reviewed research foundation moves
from R0 to R1 for the documented FIENI equation-level adaptation domain.
Production kernel stays R0; no component is moved, enabled or promoted into it.
No new backlog row is marked DONE by this review. Paper implementation matrix
labels stay unchanged, and published magnitude replication remains INCONCLUSIVE.

The [machine evidence](r1-gate-evidence.json) records 23 matching source-hash
checks, 18 passing embedded/fresh content digests, complete fresh file inventories,
all 18 R1 backlog rows DONE, and exactly equal recorded trajectories and matched
regrets for all 105 repeated scenario episodes. Timings and therefore scenario
summary/manifest hashes differ as expected; numerical/action evidence does not.
Machine-evidence content hash:
e52ecd758555b2f06ae5946ad30d6f45d9914a9552f5c2992bb43e3430a9d8d6.

Reproduce numerical acceptance from the checkout with fresh output directories:

```powershell
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
apexsim strategy-foundation-demo --output .cache/r1-foundation-new
apexsim strategy-scenarios-demo --policy-run .cache/sac-research-20261008 --output .cache/r1-scenarios-new
cd apex_engine
pytest -q
```

The scenario rerun requires the original complete R017 research artifact. On
another machine, generate the predeclared R017 research profile first; weights
and timing may differ across software/platforms, and such a new run is separate
evidence. Git history preserves the reviewed implementation and all five linked
evidence reports. Rollback of the maturity decision is a revert of this review
and project-status documentation; there are no engine changes to roll back.

Next gate: R019 must bind a multi-event collection to verified provider archives,
canonical schema versions, source/library versions and immutable hashes. The
existing British qualifying archives are development evidence, not a permanent
untouched benchmark. R020 must reserve whole previously uninspected events before
any fitting; the current split infrastructure alone does not establish that
scientific separation. R2 remains unachieved until its data/model gates pass.
