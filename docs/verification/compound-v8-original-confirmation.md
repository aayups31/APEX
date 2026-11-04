# R041 v8 original confirmation: supported Imola, unsupported Miami

Commit `be75e2c` froze the 336-window, 20-supported-event calibration before
opening Miami and Imola outcomes. No parameters were changed afterward.

| Event / labels | Blocks | Observed / predicted / matched | Pace MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|---:|
| Miami / both definitions | 0 | 0 / 0 / 0 | unavailable | unavailable | unavailable |
| Imola / difference of medians | 9 | 4 / 5 / 4 | 0.314 s | 0.682 s | 0.422 s |
| Imola / pairwise median | 9 | 4 / 5 / 4 | 0.437 s | 0.748 s | 0.456 s |

Imola passes both frozen label gates, with 100% event recall and 80% precision.
Miami's recorded global flag periods and age support leave no common clean
12-age window; its 18 different-compound pairs are unsupported. The full
original two-event result is NOT passed because Miami cannot supply any test
evidence. No forecast or numerical error is invented for its empty cohort.

The independent native/scalar audit checks all nine forecasts and the empty
event's null errors/zero counts. Imola has 29 unsupported pairs and no reference
timestamp exclusions. Primary interval coverage is 100% (pairwise 88.9%), with
mean width 1.678 s; one event/point decision disagrees under either definition.
Physical wear and causal compound effects remain unknown; scores and empirical
radii are uncalibrated.

[Original protocol](../../research/protocols/COMPOUND_EXTENDED_V8.md),
[unchanged model](compound-v8-calibration.json), [original results](compound-v8-original-results.json),
[original source archive](compound-v8-original-archive.json),
[original audit](compound-v8-original-audit.json).
Source: [OpenF1](https://openf1.org/).

A [coverage-only amendment](../../research/protocols/COMPOUND_V8_COVERAGE_EXTENSION.md)
predeclares Qatar before opening its laps. It keeps Miami in the panel,
preserves every Imola prediction and forbids any parameter update or replacement
of a supported failed race. The panel must contain at least two supported races
and EVERY supported race must pass the unchanged numeric gates. Its outcome
is separate from this retained original result.
