# ADR 0010: forecast crossover events separately from mean pace

Status: research experiment; no production promotion.

## Context

R041 v1-v5 pace regressors repeatedly reduced absolute pace error without
meeting crossover recall. V4 passed the original pairwise gate on Canada and
Austria but failed its additional difference-of-medians check in Canada. V5
failed Hungary recall and China's pairwise error comparison. Retain all results.
Eight-event development screening of field context, tree regressors and shorter
horizons did not establish a satisfactory replacement. Those diagnostics must
not be described as independent confirmation.

## Decision

A thresholded mean pace forecast is not an estimate of the probability of a
crossover event. Add a direct, balanced logistic event head to the existing
causal completed-reference pace model. Report its decision score separately
from the pace point estimate, including their disagreements. A balanced
classification score is not a calibrated event probability.

Keep nine-lap horizons, original margins, both label definitions and the numeric
recall/precision/error bars. The new protocol explicitly evaluates event
decisions from the event head and MAE from the pace head, with fresh heldout
races. No earlier rejected result is rescored as a fresh pass.

Completion, if supported, is limited to retrospective green/dry, historical
reference-conditioned public pace forecasts and event decisions. It establishes
neither physical wear coefficients nor reliable full-stint strategy forecasts.
The race kernel and maturity level remain unchanged.
