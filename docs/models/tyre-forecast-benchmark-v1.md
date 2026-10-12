# Four-wheel proxy forecast benchmark v1 model card

Task R025, ADAPTATION. The
[frozen protocol](../../research/protocols/TYRE_FORECAST_BENCHMARK.md),
[architecture map](../../research/equations/TEMPORAL_FUSION_PROXY_V1.md) and
[verification report](../verification/robust-tyre-forecast-report.md) define scope.

The complete benchmark fits ordinary linear regression, ridge, native XGBoost,
GRU, LSTM and compact TFT. Independent persistence/trend controls share their
test keys. Every target is an R024 PROXY in kJ, never measured wheel energy.
Every field retains its source truth label; measured wheel targets are UNKNOWN.

The eight-sample history includes only causal past values. Targets are four
wheels at native sample horizons 1/3/5. Eight samples represent a short,
irregular history, not the paper's 0.1-second resampling. Windows cannot bridge
sequence, driver, event or source-row boundaries. Training-only scalers and
vocabularies are persisted and independently recomputed on reload.

Training: Bahrain/Australia. Validation: Miami. Test: Monza/Singapore. Configs
are selected by mean validation RMSE across seeds 11/23, with a fixed search
budget and best validation epoch. All test tracks are unseen in this slice;
broader seen/unseen-track evidence belongs to R026. Prior dataset inspection is
disclosed; these are development tests rather than the permanent benchmark.

TFT implements variable selection, static contexts, recurrent encoding/decoding,
gated skips, enrichment, shared-value causal attention and ordered quantiles.
TFT uses pinball loss; GRU/LSTM use MSE. Attention weights are diagnostics, with
no explanation-faithfulness claim. The common nonnegative projection is visible
alongside raw errors and correction counts. TFT's nominal 80% intervals are
uncalibrated, with actual coverage reported rather than assumed.

Numeric NPZ coefficients, native UBJ trees and Torch state dictionaries reproduce
all selected test predictions without retraining. Saved raw/projected TFT
quantiles also reload. Bulk windows, predictions and weights stay ignored;
compact manifests, all trial histories, metrics and evidence are committed.

Install the forecasting extra, then run from the checkout:

```powershell
python -m pip install -e './apex_engine[dev,data-contracts,optimization,forecasting]'
.venv/Scripts/python.exe -m apexsim.cli tyre-forecast-benchmark .cache/tyre-energy-public-corrected-20261012 --output .cache/tyre-forecast-new
.venv/Scripts/python.exe -m apexsim.cli verify-tyre-forecast-benchmark .cache/tyre-forecast-new
.venv/Scripts/python.exe -m apexsim.cli tyre-forecast-smoke --output .cache/tyre-forecast-smoke-new
```

The frozen real R024 dataset seal is mandatory for research closure. The last
command generates a visibly SIMULATED execution fixture and cannot close R025.
XGBoost 3.0.5 uses its native CPU API; Linux installs the CPU-only distribution,
and Windows installs the corresponding full distribution running on CPU.

The benchmark establishes executable open-loop comparisons under the specified
budget. It does not demonstrate measured-energy accuracy, stable imagined
rollouts, intervention validity, planner performance or production promotion.
