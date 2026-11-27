# R041 field pace and individual tyre crossovers

R041 remains open. APEX can forecast part of the change in field pace on
the opened development races. Giving that forecast to the individual-car
model passes 9 of 24 supported races, the same count as the existing
baseline. Both use all 393 comparisons. The four other source races have
zero eligible comparisons.

| Input to crossover forecast | Races passing | Macro mean absolute contrast error |
|---|---:|---:|
| Nomination/practice ridge | 9 / 24 | 0.4440 s |
| Add recent pace changes from other drivers (v28) | 8 / 24 | 0.4582 s |
| Add the predicted future field change (v29) | 9 / 24 | 0.4437 s |
| Diagnostic using observed future field information | 8 / 24 | 0.4256 s |

Each outer fold holds out the whole race. The last row supplies later
peer observations and can only diagnose the influence of those features.
It uses the same downstream checkpoint as v29. The 0.0003 s difference
between v29 and the baseline provides little evidence of a pace gain.
Their passing sets differ by two gains and two losses. The predictions
are retrospective replays using the existing archive quality masks.
Availability of final quality flags in a live feed is unverified.
[Field timing protocol](../../research/protocols/COMPOUND_FIELD_EVOLUTION_V28.md),
[v28 forecasts](compound-v28-development.json),
[field forecast protocol](../../research/protocols/COMPOUND_FIELD_FORECAST_V29.md),
[v29 forecasts](compound-v29-development.json).

## What the field forecast learns

At the current forecast clock, 335 cases have a peer with six recent
clean laps and 299 have one on the same compound. In the auxiliary test
the target is the later change in the peers' three-lap median pace.
Each race receives equal weight in the reported errors. The evaluation
includes only observed matches for this auxiliary target.

| Peer group | Matched cases | Races | Predicted change | Zero change | Extrapolate recent trend |
|---|---:|---:|---:|---:|---:|
| All compounds | 334 | 20 | 0.300 s | 0.382 s | 0.509 s |
| Same compound | 284 | 20 | 0.371 s | 0.414 s | 0.614 s |

For the wider field, the predicted change improves on zero in 13 of
20 races. Feeding it to the crossover model still leaves 15 failing
races. Twelve fail at least one crossing decision requirement and
eight fail at least one pace comparison. These groups overlap.

## What still causes errors

Replacing the predicted field summary with its observed value corrects
12 crossover decisions and introduces 26 errors across the 786 decisions.
Among decisions whose observed label is stable across the registered
fuel-sensitivity range and has matched future peers, 85 are wrong under
both inputs across 12 races. The two crossover definitions can count
the same physical comparison twice. These paired results limit what
improving the field estimate alone can accomplish with this checkpoint.
[Paired error audit](compound-v29-field-errors.json).

## Does earlier individual telemetry explain the remaining pace change?

A follow-up screen measured the subject's pace change relative to the
observed field change. It used 327 nonoverlapping physical windows across
20 races, with an entire race held out for each fit. Predicting zero
individual deviation gave 0.498 s of error. Prefix timing and field
information gave 0.506 s. Adding mean speed, throttle, brake, coasting
and DRS use and their changes across the prefix gave 0.511 s. Telemetry
improved on timing in 10 of 20 races and on zero in nine. The screen
missed its preregistered criteria for expanding aggregate telemetry.
[Screen protocol](../../research/protocols/COMPOUND_INDIVIDUAL_RESIDUAL_SCREEN.md),
[window predictions and race errors](compound-individual-residual-screen.json).

The next evidence to seek is an independent observation of individual tyre
state, such as a time-stamped tyre temperature or pressure series with
driver, wheel and stint identities. First verify its coverage of the
development cohort and availability before the forecast clock. Reuse the
individual-deviation screen to measure incremental predictive value before
returning to the 393-case gate. Availability of such a source remains open.
Fresh confirmation remains sealed.

The Spa dataset shared for this investigation contains simulated tyre
channels for five Corvette C7.R laps in Assetto Corsa. The source has no
event/driver join to the R041 field. The state-space paper repository
provides Hamilton lap-time data and modeling code. OpenF1's public car
schema lists driving channels. The Hungarian GP Pirelli preview gives
prescribed starting pressures, and the race scrutineering report confirms
the checks. These sources supplied no measured per-wheel series for the
cohort. [Spa dataset card](https://huggingface.co/datasets/Nasim435/spa-francorchamps-lap-data/raw/main/README.md),
[paper repository](https://github.com/colecappello12/F1_SSM_Paper),
[OpenF1 car schema](https://openf1.org/docs/#car-data),
[Pirelli event notes](https://www.fia.com/system/files/decision-document/2025_hungarian_grand_prix_-_event_notes_-_pirelli_preview.pdf),
[FIA scrutineering report](https://www.fia.com/system/files/decision-document/2025_hungarian_grand_prix_-_race_scrutineering.pdf).

## Reproduction

```powershell
python research/scripts/compound_field_evolution.py --output .cache/v28-replay.json
python research/scripts/compound_field_forecast.py --output .cache/v29-replay.json
python research/scripts/audit_compound_field_errors.py --output .cache/v29-errors-replay.json
python research/scripts/screen_compound_individual_residual.py --output .cache/r041-individual-screen.json
```

The v28 extraction requires the previously verified native archives in
`.cache`. The v29 forecast and paired audit use tracked inputs. The tests
refit the causal forecast, check native clock boundaries and perturb a
held-out race's future peer values to verify its forecasts stay fixed.
The native extraction also replayed byte-for-byte in a fresh local output.
