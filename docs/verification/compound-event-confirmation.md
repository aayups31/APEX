# R041 direct event-head confirmation

Freeze `eba51a9` preceded Netherlands and Singapore 2025 lap acquisition. The
pace and logistic event heads used eight previously opened races only.
The heldout evaluation failed; R041 remains open.

| Event / labels | Blocks | Observed / predicted / matched events | Pace MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|---:|
| Netherlands / difference of medians | 10 | 2 / 4 / 1 | 0.342 s | 0.588 s | 0.421 s |
| Singapore / difference of medians | 24 | 9 / 7 / 2 | 0.555 s | 1.575 s | 0.924 s |
| Netherlands / pairwise median | 10 | 3 / 4 / 1 | 0.314 s | 0.586 s | 0.421 s |
| Singapore / pairwise median | 24 | 8 / 7 / 2 | 0.559 s | 1.581 s | 0.924 s |

Pace error beats both persistence baselines in both races. Event recall and/or
precision fail in both. Primary event/point decisions disagree on three and ten
cases respectively; the separate event objective does not resolve the failure.
The score is an uncalibrated balanced classification score, not a probability
of a physical compound crossover. Primary residual interval coverage is 100%
and 83.3%, with mean widths 2.030 s and 2.034 s. No reference time violations
occurred; 45 and six pairs lacked the required age support.

[Protocol](../../research/protocols/COMPOUND_EVENT_V6.md),
[decision](../architecture/adr-0010-crossover-event-head.md),
[fit and selection](compound-v6-calibration.json), [results](compound-v6-results.json),
[source manifest](compound-v6-archive.json), [independent audit](compound-v6-audit.json).
The audit independently reconstructs all 34 published cases, both native label
definitions, scalar pace/event calculations and aggregate gates. It does not
independently enumerate all excluded cohort windows. Its synthetic integration
test detects both altered point forecasts and altered event scores after resealing.
Source: [OpenF1](https://openf1.org/).

```text
python research/scripts/confirm_compound_event.py evaluate --frozen docs/verification/compound-v6-calibration.json --archive .cache/r041-event-holdout --output .cache/r041-v6-replay.json
python research/scripts/audit_compound_event.py --frozen docs/verification/compound-v6-calibration.json --results .cache/r041-v6-replay.json --archive .cache/r041-event-holdout --output .cache/r041-v6-audit-replay.json
```

Development diagnostics also retained field-context/tree and shorter-horizon
comparisons. None was advanced as independent evidence merely for lower error:
[field/tree comparison](compound-adaptation-development.json),
[matched horizons](compound-horizon-development.json).

All ten opened races are now development data. A subsequent model needs a new
frozen split; these failures cannot be silently removed from its model card.
