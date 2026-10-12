# Model card: fuel-corrected tyre pace and hierarchical drift v1

R021/R022, Gaussian-state ADAPTATION. Intended use: research on clean historical
dry laps, causal 1/3/5-lap pace forecasts and explicit uncertainty diagnostics.
It is not a physical-wear sensor, live race controller or production simulator.

R021 fits compound drift and process/observation variance with training-only
marginal likelihood. Four chronological whole-event folds test Bahrain→Australia,
then accumulated training→Miami, Monza, Singapore. Held-out prefixes update states
after observations arrive. Persistence and causal last-three-lap trend use the
same origins; per-event/compound metrics and fuel sensitivity remain visible.

R022 trains a proper Gaussian compound/track/driver random-effects hierarchy on
Bahrain+Australia only. Two blocked Gibbs chains use seeds 11/23, 1,500 warmup
and 1,500 retained draws each. Q/R are plug-in training estimates. Miami alone
fixes interval calibration; Monza+Singapore are held out. Unseen tracks retain
group-prior uncertainty. The global posterior is frozen during per-draw causal
state filtering (modular prediction, not joint updating on held-out prefixes).

The raw posterior and parameter intervals are preserved. The separate validation
adjustment narrows intervals and reduces held-out coverage to 83–85%, below
nominal 90%. It passes the preregistered 80–98% descriptive gate, but demonstrates
limited cross-track calibration transfer. No test-driven retuning was performed.
Reported mixture NLL, PIT histograms, interval widths, event/compound results and
segment-cluster bootstrap make that failure mode inspectable.

Fuel is assumed, not measured. Pace is confounded with driver, traffic, car,
weather and tyre effects. The retrospective source-quality mask does not
establish online target eligibility. Five events and two training tracks cannot
establish broad seasonal generalization. Gaussian tails remain a limitation;
R023 evaluates a [robust observation alternative](robust-tyre-observations-v1.md)
separately, with Gaussian-trained group draws/Q/R retained. Its improvement
does not repair the R022 interval-adjustment calibration shortfall.

The all-chain NPZ, configs, all predictions and sealed manifest can be reloaded
with `verify-tyre-study`. Smoke runs use fewer draws and SIMULATED observations;
`task_closure_eligible=false` prevents synthetic execution success from becoming
research acceptance evidence. Neither task changes the scoped R1 research/R0
production maturity decision. A separate R2 review is required.

See [equations/units](../../research/equations/TYRE_PACE_V1.md),
[data card](../data/tyre-pace.md) and [frozen evidence](../verification/tyre-degradation-report.md).
