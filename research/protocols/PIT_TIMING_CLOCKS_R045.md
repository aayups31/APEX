# R045 calibration from pit clocks with wider training support

Keep the first study's 2024 evaluation stops and gates. From the same
four 2023 archives, extract green entry/exit clock pairs even when
the clean prefix or peer control for a pace proxy is unavailable.
Reuse the prior clock reconciliation, inlap/outlap identity and
quality rules. Split measured lane time at the recorded finish line
clock of the inlap.

For each circuit with at least five qualifying clock pairs, use the
medians of total lane time and the two components. Add the difference
between circuit and pooled training medians of each component to the
original pooled inlap and outlap proxy estimates. Sum those differences
and add them to the original pooled total estimate. This preserves
the registered total target and its baseline, while fitting measured
lane components on the wider set. A circuit without support uses the
original pooled model. Report support, held-out accuracy and the
unchanged gate. Historical measured clock shifts are inputs to the
predictor. Held-out clock measurements only supply the targets.
