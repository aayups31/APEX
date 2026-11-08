# R041 calendar and nomination recovery

The first v20 adapter run found source conflicts. Inspection of the verified
Jolpica and FastF1 manifests establishes that 2023 R14 is Italy and R15 is
Singapore. The hardcoded adapter folders selected Netherlands and Italy.
Those mismatched inputs were rejected, with zero support. Preserve the first
run as a rejected local diagnostic. Do not claim its score as validated.

The v13 nomination inventory also assigns the Dutch C1/C2/C3 announcement to
2023 R14. The same pre-race Pirelli source announces C3/C4/C5 for Monza.
Correct R14 to C3/C4/C5 using that existing announcement. R15 is Singapore,
whose existing C3/C4/C5 nomination remains numerically consistent.

Resolve all older race folders from verified frozen calendar metadata. Require
exported meeting name AND race date to agree. For OpenF1 require exact native
session key in addition to the existing identity checks. Never infer round
identity from hand-coded event-name tables. Keep the first-run raw snapshots
and avoid using rejected Dutch observations in training.

All v20 timing, processed inputs, sample masks, 392-case cohort, output bounds,
weights and v12 prediction gates apply. Fit a corrected v17 nomination/practice
control and the same corrected control plus processed telemetry as primary.
Use identical whole-race folds. This is a metadata repair, with no parameter
or threshold selection. Publish both corrected procedures and all failures.
Independent checkpoint and gate auditing, prior regressions, calendar mapping
regressions, exact extraction replay and full CI are required.

Native provenance is still unavailable for exports. No fresh holdout acquisition
or R041 completion follows without prediction and causal timing review.
