# R027/R028 implementation correction: batch-invariant frozen inference

2026-10-30, after the first public attempt stopped at its numerical invariant and
before a completed study or inspection of its explanation/counterfactual outcomes.
The failed attempt `.cache/r027-r028-research-20261030` is preserved, incomplete.

The saved linear parameters are float32, max absolute coefficient1.778551936.
SGEMM evaluates the same input with slightly different rounding for a128-row
baseline batch and a two-row explanation batch. On the fixed128 origins, the
maximum one-row/batch difference is4.356990477294431e-6kJ, enough to fail the
existing rtol1e-6/atol1e-7 invariant near zero. This is software/numerical evidence,
not an explanation-quality or counterfactual-success result.

Use unchanged float32 input normalization and unchanged saved coefficients, with
fixed row-wise **float64 accumulation** for linear/ridge inference. Do not relax
the replay tolerance. Record the maximum baseline difference from the historical
R026 float32 predictions for every method. The initial linear128-row float32 vs
float64 difference is3.5004534448823676e-6kJ. Historical R025/R026 loaders, results,
weights, scalers and manifests remain unchanged. The new adapter implements the
same fitted linear equation with deterministic accumulation across batch sizes.

An additional numerical preflight checks all ten checkpoints on the same inputs,
without computing explanation rankings or counterfactual successes. Native neural
batch2 vs batch128 also differs by roughly1–2e-6kJ (GRU/LSTM), with failing
near-zero cells at the unchanged tolerance. For GRU/LSTM/TFT, always use native
float32 inference in fixed32-row chunks, edge-pad the final chunk and discard
padding. There is no batch normalization or cross-example attention; padding
changes no example's input. This fixes the numerical kernel shape rather than
weakening the invariant or changing parameters. Record its historical forecast
drift alongside the linear/ridge diagnostic. XGBoost is already batch-invariant.
TFT's maximum preflight difference is3.2677428576377565e-6kJ.

Add explicit batch-invariance tests. Independent audit uses separately loaded
float64 coefficients with ordinary matrix multiplication; native tree/neural
models use the older saved-checkpoint loader, with the same32-row padding for
neural inference. No cohort, donor, scenario,
faithfulness, support, crossing or acceptance threshold changes. Rerun the same
frozen cohort to a fresh output directory. Both protocol documents accompany it.

## Real-data preflight correction, 2026-10-31

The fixed32-row shape passed synthetic-checkpoint tests but the second public
attempt (`.cache/r027-r028-research-stable-20261030`, preserved incomplete) still
stopped at the unchanged invariant for GRU. Row position/other-batch-content
rounding remains visible in native float32 CPU inference. That proposed neural
fix is superseded, not treated as accepted evidence.

Evaluate loaded GRU/LSTM/TFT weights in **float64**, after the same frozen float32
input normalization. Casting preserves every stored coefficient value exactly;
there is no retraining, input change or output adjustment. Use at most256 rows
per inference chunk. Independently instantiate/reload the architecture and
evaluate selected scenarios in float64 in the audit. The original historical
float32 loaders/results remain unchanged, and every model's maximum historical
baseline drift remains reported. Add a complete128-origin, ten-real-checkpoint
batch2-vs128 numerical preflight before another public run. The original replay
tolerance and all scientific gates, cohorts, donors and scenarios remain fixed.
