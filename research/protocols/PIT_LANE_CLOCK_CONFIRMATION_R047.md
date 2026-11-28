# R047 direct pit-lane clock confirmation

The original matched confirmation had insufficient support. Its
clean-peer requirement was inherited from R045, where peers are
needed to estimate lost race pace. R047 predicts the measured time
between pit entry and exit. Verify that target directly on the same
five 2025 races. Retain the prior confirmation and the frozen
distribution, comparator, scoring thresholds and five-stop minimum.

Use positive finite OpenF1 lane durations. Require a unique reported
driver and pit lap, within the session window and with a native lap
record on that lap or the next flagged outlap. Require the interval
from one reported lane duration before the pit timestamp through
one duration after it to be entirely under green status. This guards
against ambiguity in the pit timestamp within the stop. Exclude
session-opening stops by requiring start of lap three or later.
Keep slow measured stops and all denominators. Confirm the green
pit-lane observable only. Report the wider source cohort and its
difference from the R045 clean-peer target sample.
