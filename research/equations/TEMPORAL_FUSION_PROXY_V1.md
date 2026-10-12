# Matched four-wheel proxy forecasting v1

R025 is a public-data ADAPTATION of the Todd forecasting workflow and
[Lim et al., TFT, arXiv:1912.09363v3](https://arxiv.org/html/1912.09363v3).
Sections 3–5 inform the architecture below. Private measured wheel energy,
paper training budgets and published scores are not reproduced.

## Information and targets

Every method receives eight consecutive native past samples, including the
origin, with the same 14 dynamic fields and three static families. Four target
values are energy proxies in kJ at 1/3/5 native samples ahead. Time intervals
remain irregular; neither future elapsed duration nor actual future telemetry
is supplied. The only decoder covariate is the predetermined horizon index.

Sequences cannot cross events, drivers, compounds, segments or native-row gaps.
Numeric scalers and static vocabularies fit Bahrain/Australia only. Miami selects
configurations; Monza/Singapore score them. Unseen categories receive UNKNOWN.
These are reused development events, with all test tracks unseen in this slice;
R026 requires a separate broader seen/unseen design.

## TFT component map

| Source component | `apexsim.research.temporal_fusion` implementation |
| --- | --- |
| GRN with optional context, ELU, GLU gate, residual and normalization | `GatedResidualNetwork` |
| Per-variable embeddings, GRNs and contextual softmax selection | `VariableSelection` |
| Static selection and four contexts | `static_selection`, `contexts` |
| Local recurrent processing and gated skip | LSTM `encoder`/`decoder`, `local_gate`, `local_norm` |
| Static enrichment | `enrichment` |
| Shared-value interpretable multihead attention | `SharedValueAttention`, averaging two heads |
| Causal attention | Upper triangular future-position mask |
| Position-wise processing and skip around transformer | `position_grn`, `final_gate`, `final_norm` |
| Multi-horizon quantile output | Four-wheel .1/.5/.9 heads, selected horizons 1/3/5 |

Ordered quantiles use median `m`, lower `m-softplus(l)` and upper
`m+softplus(u)`. Pinball loss is the mean of
`max(q*(y-yhat), (q-1)*(y-yhat))`. The median is the point prediction.
GRU/LSTM use point MSE; objectives and training cost differ explicitly. Static
UNKNOWN input columns are initialized to zero so unsupported categories do not
introduce arbitrary untrained input weights.

Ordinary least squares, ridge and genuine native XGBoost complete the six fitted
families. Persistence and last-three-energy trend are independent causal
controls. The native XGBoost 3.0.5 Booster API avoids sklearn wrapper-tag
incompatibility without changing frozen tree settings. Numeric NPZ linear
weights, UBJ trees and `weights_only=True` Torch state dictionaries are reloadable.

All outputs use a declared common nonnegative projection. Raw predictions,
projected predictions, correction counts and magnitudes are retained. TFT raw
and projected quantiles are saved; their nominal 80% intervals are uncalibrated.
Configuration selection uses validation physical-unit RMSE averaged over the
fixed seeds. Sequence-cluster bootstrap comparisons preserve frame correlation.

This is a compact CPU implementation with a fixed 12-epoch budget, short native
histories and proxy targets. Attention/selection weights are diagnostics, not
evidence of explanation faithfulness. No autonomous rollout, planner or
production promotion follows from an open-loop forecasting benchmark.
