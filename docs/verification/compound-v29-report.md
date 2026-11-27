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

The next test is to forecast the individual car's pace change relative
to contemporaneous peers. Use earlier driver/stint telemetry and train
on clean, nonoverlapping twelve-lap windows from other races. Compare
against a zero individual deviation on matched windows, then score all
393 crossover forecasts with the existing fallback and gates. This tests
whether the remaining car-specific variation is predictable before
acquiring further race outcomes. Fresh confirmation remains sealed.

## Reproduction

```powershell
python research/scripts/compound_field_evolution.py --output .cache/v28-replay.json
python research/scripts/compound_field_forecast.py --output .cache/v29-replay.json
python research/scripts/audit_compound_field_errors.py --output .cache/v29-errors-replay.json
```

The v28 extraction requires the previously verified native archives in
`.cache`. The v29 forecast and paired audit use tracked inputs. The tests
refit the causal forecast, check native clock boundaries and perturb a
held-out race's future peer values to verify its forecasts stay fixed.
The local compound regression suite passed all 142 tests.
