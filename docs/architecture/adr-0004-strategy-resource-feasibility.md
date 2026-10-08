# ADR 0004: Fail on unreachable strategy resources and benchmark finite-grid optima

- Date: 2026-10-08
- Status: accepted
- Scope: research FIENI adaptation R012-R014; no sim_core change

The supplied paper and the starter differ in normalized battery mapping. The
starter's finish projection can also exceed per-lap deployment limits, and its
beam solver can return an illegal residual-energy finish. Silent correction is
incompatible with the master guide's resource and oracle contracts.

Use the paper's affine normalization and intersect per-lap input, state and
next-state backward-reachable bounds. Reject infeasible initial conditions and
invalid/unreachable intermediate states. Preserve requested/applied actions and
record correction reasons plus wear saturation. The supplied Eq. 59's depletion
sign/index ambiguity is explicitly documented in the equation review.

Add bounded exhaustive finite-grid enumeration independently of beam search.
Expose lossless future-state dominance and pruning evidence in beam exact mode.
Default coarse/finite-width beam remains approximate; no legal terminal candidate
means an explicit failure, not fallback to an illegal finish.

This changes experimental strategy API behavior for infeasible inputs and
normalized battery midpoints. Synthetic coefficients and missing paper mechanisms
remain declared adaptations. No production planner or learned policy is promoted.
Rollback is a code revert; historical artifacts remain untouched.
