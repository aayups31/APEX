# Frozen track-generalization evaluation v1 model card

R026 is a retrospective DEVELOPMENT ADAPTATION, using the frozen R025 linear,
ridge, XGBoost, GRU, LSTM and compact TFT checkpoints. The ten selected weights,
training-only scalers/vocabularies and validation-selected family are unchanged.
No model, scaler, vocabulary or interval calibration is fitted on R026 data.

Training was Bahrain/Australia2024; validation was Miami2024. Evaluation uses
Bahrain/Australia2023 as seen circuits and Monza/Singapore2023 as unseen circuits.
Seen means membership in the training circuit vocabulary. These are separate
events from every training/validation/test event used by R025. Both evaluation
strata share a season. This is not prospective deployment; car, driver, regime
and circuit-layout changes confound a causal interpretation of track novelty.

Every model and control receives the same eight native past samples, four-wheel
targets and native sample horizons1/3/5. Actual elapsed durations remain visible.
The R024 physical proxy equations, priors, quality mask and 50-field truth/unit
contracts are retained; measured wheel quantities remain UNKNOWN. Source traces
keep native rows, backward-only motion support and explicit exclusions.

Primary scores give equal weight to events: sqrt(mean(event MSE)). Frame-weighted
scores, seed-specific results, raw/projected errors and per-wheel/horizon/event
metrics are also saved. Uncertainty resamples events then whole sequences within
events, pairing each candidate against persistence. Family statistics average
seed losses on the same examples; they are not ensemble predictions or additional
independent events. Only two events/circuits per stratum limit population claims.

TFT raw/projected quantiles are retained with actual nominal80% coverage and
width. Native interval outputs are uncalibrated. The frozen family decision does
not promote production or establish measured wheel-energy accuracy.

From the checkout, using fresh paths and the four trusted archives:

```powershell
.venv/Scripts/python.exe -m apexsim.cli build-track-generalization-dataset --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r3-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --archives .cache/r026-fastf1-2023-r15-race-20261013 --calendar .cache/jolpica-2023-20260916 --output .cache/r026-proxy-new
.venv/Scripts/python.exe -m apexsim.cli track-generalization-demo .cache/r026-proxy-new --reference .cache/tyre-forecast-research-20261012 --output .cache/r026-evaluation-new
.venv/Scripts/python.exe -m apexsim.cli verify-track-generalization .cache/r026-evaluation-new
```

Portable evaluation artifacts copy the original weights/scaler and reference
manifest, input metadata, stored windows and all point/quantile predictions.
Reload replays inference and recomputes diagnostics, confidence and decisions
without source caches or fitting. Original native-source reconstruction remains
a separate verified archive/data-builder workflow; portable replay does not
authenticate the provider or rederive every proxy from original sensors.

Use `track-generalization-smoke --reference <six-family-smoke-run> --output
<fresh-directory>` for visibly SIMULATED execution checks. Smoke cannot close R026.
See the [frozen protocol](../../research/protocols/TRACK_GENERALIZATION.md) and
[verification report](../verification/track-generalization-report.md).
