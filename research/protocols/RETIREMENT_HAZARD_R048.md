# R048 all-cause retirement prototype

Use the public FastF1 results tables from the R045 v1 source inventory.
Fit on four 2023 races and evaluate on five 2024 races. Bind each table
to the same verified archive. Finished and lapped starters contribute
exposure through their completed lap count. A retired starter contributes
one event in the lap after their completed laps and exposure through that
lap. This reconstructs a lap-level label from finishing classifications.
Exclude documented nonstarters and unresolved classifications with counts.

Use a Jeffreys Beta(0.5, 0.5) prior and compare constant hazard with
separate first-lap and subsequent-lap hazards. Compare summed
Bernoulli log loss on held-out driver laps and report race counts and
expected counts conditional on realized exposure. This fits all-cause
retirement. Cause-specific incident and mechanical failure hazards
require source labels with verified coverage before R048 closes.
