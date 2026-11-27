# R045 expanded same-circuit training

Add the 2022 Australia, Miami and Singapore races as training-only
sources. A requested 2023 Miami archive contained no lap timing after
retry, so the frozen expansion uses the 2022 source for Miami. This
source decision was made before extracting or scoring the added stops.
Apply the original green-clock and
peer-control filters. These circuits were selected for missing
training support in the first study. Keep all 110 held-out stops and
the original pooled 2023 comparator frozen. Also score an expanded
pooled comparator to separate the benefit of circuit conditioning
from the benefit of additional data.

Use the original per-circuit medians and minimum five-stop support.
An unsupported circuit uses the expanded pooled estimates. Require
the original acceptance gate and lower race-average total error
against the expanded pooled comparator. Record both comparisons,
archive identities and all skipped stops. Reuse the same extraction
and scoring functions. No 2024 observations enter either fit.
