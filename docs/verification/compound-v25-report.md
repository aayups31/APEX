# R041 distance-aligned speed profiles

R041 remains open. Distance-aligned speed features pass 9 of 24 supported
whole-race development folds. The existing native telemetry control passes
the same nine races. The corrected dataset and native input verification
remain useful for subsequent candidates.

## Experiment

The v25 candidate uses the independently audited [pit-exit cohort](compound-v24-report.md)
of 393 comparisons across 28 opened races. It adds seven inputs to the
native ridge model. Native speed is integrated within each known lap clock
and sampled at 64 equal-distance bin centers. The three completed
reference-prefix laps set the slow and fast bins. Median speed differences
and current-prefix trends are computed in these same bins, with a support
indicator when the profiles satisfy time and distance coverage.

The independent implementation audited 3,346 distinct physical laps with
scalar integration and interpolation. All nine profiles met support on
377 of 393 comparisons. The model retains all 393 comparisons, with a
missing-support indicator on the other 16. Current target telemetry is
outside the feature window. Distance is reconstructed from speed and
does not identify a physical corner or tyre wear.

| Same corrected cohort | Supported races passing | Macro mean absolute error |
|---|---:|---:|
| Native ridge | 9 / 24 | 0.468 s |
| Native ridge plus distance-aligned speed | 9 / 24 | 0.473 s |

Both models exclude the full test race and predict three future lap times.
Each is independently checked for training objective stationarity and
checkpoint inference. The original pace and crossover decisions are
replayed for 48 race-label combinations per model. Four opened races
remain recorded with zero eligible comparisons. No model is accepted for
new holdout acquisition or production.

## Next evidence

The v24 fuel diagnostic found 174 comparisons whose observed crossover
changes over the registered fuel range. The robust v24 candidate also
missed 73 fuel-stable decisions. The OpenF1 and FastF1 native car channels
include speed, throttle, braking, gears and RPM. Neither publishes
per-lap fuel mass or fuel flow. More of these same samples can add race
coverage and cannot directly measure fuel. [OpenF1 car channels](https://openf1.org/docs/#car-data),
[FastF1 native car channels](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/_api.py).

A follow-up matchability audit tested equal tyre ages, at most one race lap
apart and within 30 seconds. It found 882 candidate windows in 25 of the
28 opened races. Only 49 windows in seven races had six prior, distinct
same-compound control laps for the exact driver pair. Connecting drivers
through other pairs with the same minimum support raises this to 72
windows in eight races. Two races contribute 55 of the 72. These counts
measure available comparisons, with some physical laps shared across
pairs. No crossover labels were scored. [Same-phase support audit](compound-same-phase-connected-support.json).

Use this smaller cohort to test whether causal driver controls reduce
crossover error, with same-compound negative controls and uncertainty
reported near the pace margin. Compare it with the original v12 gates
and keep its independent scope visible. The wider model still needs
either better pre-race or in-race controls, or measured fuel and other
vehicle state. Once a candidate qualifies on complete development gates,
confirm it on fresh races before R042 uses it.

## Reproduction

The profile extraction, v24 fuel sensitivity and same-phase support audit
replay byte-for-byte from local native archives. The v24 and v25 model
refits also reproduce exactly locally. On GitHub, Python 3.11 and 3.12
each pass 900 tests, both forecast replays, the package builds, and every
simulator verification step. The local Windows run on Python 3.12.12
also passes all 900 tests, with two dependency deprecation warnings.
[Verification receipt](compound-v25-final-review.json).

```text
python research/scripts/compound_speed_profile.py --output <fresh-profiles.json>
python research/scripts/compound_speed_profile.py --profiles <fresh-profiles.json> --expected docs/verification/compound-v25-development.json --output <fresh-refit.json>
python research/scripts/audit_compound_same_phase_support.py --output <fresh-support-audit.json>
```

[Frozen protocol](../../research/protocols/COMPOUND_SPEED_PROFILE_V25.md),
[native profile evidence](compound-v25-speed-profiles.json),
[refit and gate results](compound-v25-development.json) and
[CI](https://github.com/aayups31/APEX/actions/runs/42921036905).
