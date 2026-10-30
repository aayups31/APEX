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
