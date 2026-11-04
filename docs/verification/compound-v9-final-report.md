# R041 bounded v9: prospective rejection

**R041 remains IN_PROGRESS.** The new implementation and artifact verification
pass, but the frozen model fails Japan. Research inventory stays 40/73 DONE;
foundation R1, production R0, with no component promotion. R042 remains next
after R041 has valid acceptance evidence.

## What is delivered

- A bounded learned pace correction, train-only scaling, compound support
  checks, explicit persistence fallback and per-case correction diagnostics.
- Source-bound causal tyre-age/weather/completed-field context: 358 development
  cases from 22 supported/24 source races, preserving both empty source events.
- Nested whole-event selection, empirical cross-event uncertainty, matched
  unbounded-ridge/tree baselines and both contrast label definitions.
- Independent scalar audits of all 358 nested forecasts and native checks of
  2,070 development field associations, plus the separately frozen fresh panel.
- Tests for future-data isolation, duplicate targets, UTC joins, stale/missing
  weather, support exits, numerical inputs, tampering, and failed-event retention.
- One offline verification command, exact coefficient refits, exact complete
  nested rerun, exact prospective replay and 34 real-case future-target mutations.

The selected model uses the original pace features; the added context did not
win development selection. The [development report](compound-v9-development-report.md)
retains the important limitation that unbounded ridge and the tree beat the
bounded model's average development error. Bounds limit learned influence;
they do not ensure accuracy.

## Prospective result

Model, source and four-race protocol were committed/pushed as `b275e0e` before
new lap acquisition. All four races remain in the result. Both heads and their
thresholds stayed frozen after acquisition.

| Race / labels | Cases | Observed / predicted / matched | Pace MAE | Contrast persistence | Reference persistence | Result |
|---|---:|---:|---:|---:|---:|---|
| Japan / difference of medians | 20 | 0 / 2 / 0 | 0.580 s | 0.543 s | 0.470 s | FAIL |
| Japan / pairwise median | 20 | 0 / 2 / 0 | 0.583 s | 0.507 s | 0.474 s | FAIL |
| Saudi Arabia / difference of medians | 14 | 2 / 2 / 2 | 0.328 s | 0.512 s | 0.373 s | PASS |
| Saudi Arabia / pairwise median | 14 | 1 / 2 / 1 | 0.282 s | 0.507 s | 0.350 s | PASS |
| Britain / both | 0 | unavailable | unavailable | unavailable | unavailable | INCONCLUSIVE |
| Las Vegas / both | 0 | unavailable | unavailable | unavailable | unavailable | INCONCLUSIVE |

Japan fails BOTH pace comparisons and produces two false crossover alarms.
It is a supported failed negative control and cannot be dropped. Saudi Arabia
passes both gates, but supplies only one informative race; the protocol needs
two. Britain and Las Vegas have no eligible common-age comparison windows under
the frozen retrospective mask. Their unsupported-pair counts are 2 and 25;
they supply neither error nor positive crossover evidence.

The unbounded ridge comparator also fails Japan (0.660/0.673 s MAE), and is
worse than the bounded model at Saudi Arabia (0.420/0.368 s). Thus bounding
improves this fresh comparison but does not solve the generalization problem.
There are 12 bounded-correction cases and one support fallback among 34 cases.
All 34 have completed field context. Context availability alone does not establish
that the selected model uses it effectively.

Frozen intervals are 2.320 seconds wide and cover all 34 outcomes under both
labels. This small-panel 100% coverage does not establish calibrated uncertainty
or compensate for false alarms and baseline regressions. Scores remain
uncalibrated; physical wear and causal tyre effects remain unknown.

## Verification

The [offline receipt](compound-v9-verification.json) records exact bounded/event
coefficient refits, complete nested replay, prospective replay, native/scalar
audits and future-target mutation invariance in all 34 real cases. The fresh
audit independently reconstructs labels, clocks, context, both candidate heads,
the unbounded comparator and main acceptance metrics. It audits 203 fresh field
contributions. Audit scope is all published cases/associations, not independent
full excluded-cohort enumeration.

The existing full local baseline passed **787 tests** in 1,144.36 seconds.
The complete old/new R041 targeted set passed **32 tests**. Repository and new
script lint pass. Research and six-car/six-lap baseline demos run with zero race
quality violations. The frozen implementation passed **801 tests on each Python
3.11/3.12 CI job**, with every artifact step green. [Completed source CI](https://github.com/aayups31/APEX/actions/runs/41858104444),
[sealed CI review](compound-v9-ci-review.json). This green code matrix does not
change the failed empirical model result.

## Reproduce

Run from the repository root in the recorded project environment. Outputs must
use fresh paths. The full development rerun is optional and takes several minutes.

```text
python research/scripts/diagnose_compound_bounded.py --dataset docs/verification/compound-v9-development-data.json --output .cache/r041-v9-new-development-replay.json
python research/scripts/verify_compound_bounded.py --archive .cache/r041-v9-confirmation-20261104 --development-replay .cache/r041-v9-new-development-replay.json --output .cache/r041-v9-new-verification.json
```

The verifier needs the original native development archives in `.cache` to
independently inspect associations. The committed source/data/parameter hashes
and [native archive manifest](compound-v9-archive.json) identify exact inputs;
bulk provider payloads remain in the ignored native cache. Verification performs
no network requests. Exact refits require the recorded numerical environment.

[Frozen model](compound-v9-calibration.json), [fresh results](compound-v9-results.json),
[fresh native/scalar audit](compound-v9-confirmation-audit.json),
[development summary](compound-v9-development-summary.json),
[full compressed development evidence](compound-v9-development.json.gz),
[prospective protocol](../../research/protocols/COMPOUND_BOUNDED_CONFIRMATION_V9.md).

## Next work

1. Diagnose event-dependent drift and false alarms using the now-opened races.
   A bounded correction plus a pooled classifier is insufficient. Separate the
   question of learning a pace change from the decision to trust it.
2. Require negative-control and event-level robustness during development
   selection, rather than qualifying a model only on macro error and pooled
   precision/recall. Preserve v9's registered qualification result unchanged.
3. Evaluate causal event adaptation and reliability selection against reference
   persistence, including all fallback errors. The added context has native
   support; its predictive value still needs to be demonstrated.
4. Freeze another untouched confirmation only after the stronger development
   evidence exists. Do not spend more holdouts looking for a convenient pass.

No third API or private-data purchase is currently required. The immediate
failure is unsupported trust in a learned correction, not missing source access.
The next experiment must establish predictive value, not add model size.
