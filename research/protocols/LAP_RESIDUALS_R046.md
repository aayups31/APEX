# R046 clean-green next-lap research kernel

Use the nine verified R045 FastF1 race archives. Train on the four
2023 races and evaluate on five 2024 races. The production kernel
has no accepted calibrated full-field lap map. This experiment
calibrates a separate one-step model conditional on observed clean
laps. It can certify that restricted scope of residual modeling.

Use the existing native tyre segment mask. Keep four consecutive
completed dry-compound, green, accurately timed nonpit laps in one
stint, with ordered lap-end clocks. Forecast the fourth from the
first three. Use raw pace as the outcome. Predict change from the
last completed lap by ridge with alpha 10, using the two previous
step changes, last known tyre age, last race lap and compound
indicators. Give events equal training mass and scale on training
races only. Compare against last-lap persistence.

Build the error distributions from whole-race cross-fitted 2023
predictions. Use an equally weighted mixture of the driver's
empirical errors and pooled errors if a driver has at least 30
residuals from at least two training races. Otherwise use pooled
errors. Apply the identical construction to persistence. Keep
all scored test windows and report per-driver coverage.

The restricted gate requires lower race-average point MAE and
lower equally race-weighted CRPS than persistence, nominal 80%
interval coverage between 70% and 90% overall, coverage at least
60% in each held-out event and at least 50 observations per event.
This checks a retrospective conditional model with source flags.
Closed-loop full-field calibration and production promotion require
separate evidence.
