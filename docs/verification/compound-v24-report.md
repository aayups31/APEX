# R041 pit-exit cohort review

R041 remains open. The pit-exit repair reconciles a native timing discrepancy
and has been independently rebuilt across all 28 previously opened races.
The corrected model results still fall short of the existing development
requirements. Fresh confirmation races remain sealed.

## Source and eligibility

For OpenF1 stints after the first lap, APEX now shifts the age anchor by one
lap when the archived reported start is explicitly not a pit-out, the next
lap is explicitly a pit-out, and the two native start clocks increase. The
initial tyre-age prior, driver, compound, reported stint interval, fuel
correction, dry/green masks and native FastF1 TyreLife are preserved. The
pit-out lap is excluded. The audit checks that every corrected retained lap
follows the observed exit by lap number and clock.

The rule shifts 29 stint anchors at the 2025 Canadian Grand Prix and none at
the other opened races. Canada's eligible comparisons increase from 11 to
12. Five physical current windows are added and four removed within their
stint pairs. The seven shared current windows are reindexed, six use a
different physical reference window, and one changes from a positive to a
negative paired-median crossover. The difference-of-medians decisions on the
shared windows are unchanged.

The original 392 comparisons were independently reproduced. The rebuilt
cohort has 393 comparisons from 24 supported races. The four races with
zero eligible comparisons are still recorded. The native telemetry
extraction reused 219 sealed OpenF1 driver receipts and recovered nine
bounded intervals for Canada. It verified the prior summaries of reused
physical laps and provides all three telemetry groups for 390 of 393
comparisons. The remaining three keep explicit missing support.

## Whole-race holdout results on opened development

| Model | Races passing | Macro mean absolute error |
|---|---:|---:|
| Prior nomination and practice ridge, original cohort | 11 / 24 | 0.440 s |
| Prior native telemetry ridge, original cohort | 9 / 24 | 0.460 s |
| Nomination and practice ridge, corrected cohort | 9 / 24 | 0.444 s |
| Native telemetry ridge, corrected cohort | 9 / 24 | 0.468 s |
| Robust native telemetry, corrected cohort | 8 / 24 | 0.464 s |

Each fit excludes the entire test race. All models emit three lap times
from which both crossover decisions are derived. The independent audit
replays each checkpoint and all 48 race-label gate sets per model. The
maximum scaled gradient of the robust fit is 4.982 × 10⁻⁸, within
the registered 10⁻⁷ tolerance. The robust fit improves mean error
slightly relative to the corrected native ridge and passes one fewer race.

## Fuel assumption diagnostic

Holding native lap identities and durations fixed, the audit checks the
entire registered fuel sensitivity interval from 0.020 to 0.040 s/kg,
including pace-order swaps and threshold crossings between sampled
coefficients. At least one crossover label changes within that interval
in 174 of 393 comparisons. Across the fuel-stable labels, the robust model
still makes 73 incorrect decisions across 15 races. Measured fuel or a
better correction would address label uncertainty, and the stable-label
misses also require better forecast inputs or modeling. This diagnostic
does not change the registered labels or scoring.

## Evidence

The cohort, native telemetry extraction and model refit each replay
byte-for-byte from the saved inputs in the local environment.

```text
python research/scripts/prepare_compound_pit_exit.py --output <fresh-cohort.json>
python research/scripts/prepare_compound_pit_exit_telemetry.py --data <fresh-cohort.json> --output <fresh-telemetry.json>
python research/scripts/diagnose_compound_pit_exit.py --data <fresh-cohort.json> --telemetry <fresh-telemetry.json> --expected docs/verification/compound-v24-development.json --output <fresh-refit.json>
python research/scripts/audit_compound_pit_exit_residuals.py --output <fresh-residual-audit.json>
```

[Frozen protocol](../../research/protocols/COMPOUND_PIT_EXIT_V24.md),
[cohort and independent denominator audit](compound-v24-cohort.json),
[native telemetry](compound-v24-telemetry.json),
[results and gate replay](compound-v24-development.json) and
[fuel residual audit](compound-v24-residual-audit.json).
