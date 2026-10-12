# R025 frozen matched proxy forecasting benchmark

2026-10-12, baseline018c198. R024 dataset seal7793df65b58884be74529ecf3114ccf2efc310d0a3dd99dfa9edec4d961c2272.
ADAPTATION of Todd forecasting and Lim et al. TFT (arXiv1912.09363v3,2020-09-27).
TFT source architecture sections4–5 reviewed; this compact four-target variant
is not a paper/dataset reproduction. All targets remain R024 PROXY kJ.

Train Bahrain+Australia; validation Miami; test Monza+Singapore. Only train fits
numeric scalers and static vocabularies. Unknown driver/compound/track levels use
explicit UNKNOWN categories. All events are non-benchmark development races;
earlier descriptive dataset inspection is disclosed. No test tuning or promotion.

Eight past consecutive samples including the origin; direct horizons1/3/5 native
samples ahead, same origins across all models and all horizons. Reject any window
crossing sequence/event/driver/stint or native-row discontinuities. Preserve native
irregular times; report elapsed-horizon quantiles, not fixed0.1s forecasts. No
future controls, geometry, flags, interval duration or target enters inputs.
Dynamic inputs: speed,throttle,binary-pressure proxy,longitudinal acceleration,
lateral/steering proxy,heading rate,geometry speed,past dt,position lag,and four
past energy values. Static inputs: training-vocabulary driver,compound,track.

Methods: persistence; causal last-three-energy trend; ordinary linear least
squares; ridge alpha.1/10; XGBoost3.0.5 hist150 trees depth3/5,learning_rate.05,
subsample.9,colsample.9,n_jobs1,seeds11/23; GRU/LSTM/TFT seeds11/23 with two
fixed candidates(hidden16,lr.001) and(hidden32,lr.0003). Neural budget12 epochs,
batch512,AdamW weight_decay.0001,gradient norm1,patience3. Select config by mean
validation physical-unit RMSE across seeds; best validation epoch per seed, never
test. Each architecture receives exactly the same feature information, rows,
targets and horizons. Native training costs/objectives are disclosed, not equalized.

TFT adaptation must include per-variable embeddings/GRNs and softmax variable
selection, static contexts, LSTM encoder/decoder, gated residual skips, static
enrichment, shared-value interpretable multihead attention with causal masking,
position-wise GRN and ordered .1/.5/.9 quantile heads. Only predetermined horizon
index is known to the decoder; no future covariates or teacher forcing. Its median
is the point forecast, trained with quantile loss. GRU/LSTM use point MSE.
Attention/selection weights are diagnostics, not explanation-faithfulness evidence.

All methods use a declared common nonnegative output projection; report raw and
projected errors plus counts/magnitudes. All targets and forecast keys are saved.
Metrics: per-wheel/horizon/event MAE,RMSE,SMAPE(epsilon.001kJ),parameter count,
fit/inference time and validation histories. Confidence comparisons cluster by
sequence (500 resamples seed2025). Neural seeds and chosen configuration are
reported separately; no model is accepted because it is larger. Best validation
method is selected before test metrics; any test underperformance remains visible.

Completion: all six requested model families genuinely fit training data; one
matched frozen benchmark covers all test rows, with no leakage, finite outputs,
independent baselines, saved weights/scalers/configs/predictions and exact checkpoint
reload checks. Pipeline/execution smoke is explicitly not research closure. Full
regression,lint and Python3.11/3.12 CI pass. R026 broader seen/unseen evidence and
production promotion remain separate; no forecasting superiority is required to
mark R025 DONE, only a complete honest benchmark and accept/reject results.
