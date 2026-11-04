# R041 final disposition for this implementation run

**R041 is not complete. The latest frozen candidate fails independent pace
validation in Qatar.** Research inventory remains 40/73 DONE; foundation R1
and production R0 remain unchanged. No component is promoted.

## Delivered implementation and evidence

- A timestamp-checked completed-reference forecast: an earlier stint curve is
  used only after its contributing laps have finished. Future current-stint
  targets do not enter either forecast head.
- A six-coefficient weighted ridge pace head and a ten-coefficient-plus-intercept
  event head, with plain-JSON normalization/parameters, portable text hashes,
  immutable source archives and explicit unsupported cases.
- Source-verified training expansion: 336 windows from 20 supported races
  across 2023–25, with 21 source events. One source event has zero support.
- Whole-event development selection, original pairwise and additional
  difference-of-medians labels, matched persistence baselines, empirical
  uncertainty diagnostics, native/scalar independent audits and exact replay.
- Native UTC, weather/yellow exclusions, age-gap, permanent-benchmark, future
  label mutation, tamper detection and empty-support/enrollment tests.

All earlier attempts and rejections remain in version control. Lower pace
error in an individual experiment was never converted into an acceptance pass
when its crossover or robustness gate failed.

## Frozen v8 confirmation

The model was frozen in `be75e2c` before Miami/Imola acquisition. Imola passes
both label gates. Miami has zero eligible clean common-age windows. The original
two-event result remains not passed and is preserved separately.

The coverage-only amendment was frozen in `5cb8095` before Qatar acquisition.
It retains Miami, preserves every original Imola forecast/metric, and changes
neither head nor its threshold. It permits filling an empty cohort, while
explicitly forbidding replacement of a supported failed event. Qatar supplies
13 supported windows and fails. It cannot be discarded to make this panel pass.

| Event / labels | Windows | Observed / predicted / matched events | Pace MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|---:|
| Miami / both | 0 | 0 / 0 / 0 | unavailable | unavailable | unavailable |
| Imola / difference of medians | 9 | 4 / 5 / 4 | 0.314 s | 0.682 s | 0.422 s |
| Imola / pairwise median | 9 | 4 / 5 / 4 | 0.437 s | 0.748 s | 0.456 s |
| Qatar / difference of medians | 13 | 0 / 0 / 0 | 0.801 s | 0.494 s | 0.349 s |
| Qatar / pairwise median | 13 | 0 / 0 / 0 | 0.839 s | 0.486 s | 0.387 s |

Imola's event recall is 100% and precision 80%. Qatar has no observed crossover
and no false alarms, but its pace error is worse than both baselines. It also
cannot provide positive crossover confirmation. Primary interval coverage in
Qatar is 61.5% (pairwise 46.2%), with mean width 1.730 s, below the descriptive
90% training-residual target. The learned correction is not safe to trust
across these regimes.

The independent audit reconstructs every one of the 22 supported native cases,
both heads and label definitions, empty-event handling and panel disposition.
Its scope is all published cases; it does not independently enumerate the
complete excluded-cohort denominator. The complete panel replays exactly;
the offline v8 refit reproduces exactly. In-memory mutation of future labels
leaves both predictions unchanged in all 22 cases.

## Reproduction and artifacts

[Frozen model](compound-v8-calibration.json),
[training base](compound-multiseason-training.json),
[append-only training cases](compound-v8-training-additions.json),
[development selection](compound-v8-development.json),
[original confirmation](compound-v8-original-confirmation.md),
[coverage protocol](../../research/protocols/COMPOUND_V8_COVERAGE_EXTENSION.md),
[coverage freeze](compound-v8-coverage-freeze.json),
[complete panel results](compound-v8-coverage-results.json),
[source panel manifest](compound-v8-panel-archive.json),
[independent audit](compound-v8-coverage-audit.json),
[replay/refit/causality verification](compound-v8-verification.json).

Run from the repository root using the project Python environment:

```text
python research/scripts/confirm_compound_v8.py fit --output .cache/r041-v8-refit-new.json
python research/scripts/confirm_compound_v8_coverage.py evaluate --freeze docs/verification/compound-v8-coverage-freeze.json --archive .cache/r041-v8-confirmation-panel --output .cache/r041-v8-panel-new.json
python research/scripts/audit_compound_v8_coverage.py --frozen docs/verification/compound-v8-calibration.json --results .cache/r041-v8-panel-new.json --archive .cache/r041-v8-confirmation-panel --output .cache/r041-v8-panel-new-audit.json
```

The baseline local suite passed 772 tests from `apex_engine`; later targeted
tests cover all added behavior. The final coverage source freeze passed **787
tests on each Python 3.11/3.12 CI job**, including the repository artifact
commands. [Completed source CI](https://github.com/aayups31/APEX/actions/runs/41770984455),
[sealed CI review](compound-v8-ci-review.json). Code verification passes;
the independent model-accuracy gate above still fails.

## Required next work before R041 can close

1. Develop a bounded pace-residual model with an explicit support check and
   validation-selected persistence fallback. Count fallback errors on the same
   cohort; never remove difficult supported cases.
2. Test tyre-age and observed prefix weather/traffic context, with every join
   constrained to forecast time. Existing simple field and longer-history
   diagnostics did not establish a passing replacement.
3. Calibrate uncertainty on held-out events rather than treating training
   residual quantiles or balanced classification scores as confidence.
4. Freeze a new model and untouched event panel, including coverage enrollment
   rules and no-crossover control cases, before inspecting fresh outcomes.
5. Close R041 only after its prospective gates pass; then resume R042.

This task concerns effective public lap pace. Fuel is a prior; timing is
provider-parsed source; physical tyre wear and causal compound effects remain
unknown. These results do not establish a production race strategist or a
validated world model. Sources/terms: [OpenF1](https://openf1.org/),
[FastF1](https://docs.fastf1.dev/).
