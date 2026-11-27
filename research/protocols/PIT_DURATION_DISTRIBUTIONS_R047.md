# R047 green pit-lane duration distributions

Use the sealed R045 v1 and v3 samples. Train on 2022–2023 and
evaluate on the 110 retained 2024 stops by race. Model the
recorded positive pit-lane entry-to-exit duration including service.

Compare the pooled empirical distribution with a circuit-scaled
empirical distribution. For each training stop divide its duration
by the median of its training circuit if that circuit has at least
five examples; otherwise omit it from the ratio fit. For a
supported test circuit multiply all retained ratios by its
training median. Use the pooled empirical distribution for
unsupported circuits. Keep every test case and measure CRPS,
central 80% interval coverage and interval width by race.

Require lower equally race-weighted mean CRPS, central coverage
between 70% and 90% across all stops, at least 50% coverage in
every event, and explicit fallback. The training and test
archives were previously opened for R045. This test addresses
green pit-lane duration reproducibility over the declared sample.
