# R041 relative outlap pace forecast

Relative outlap pace had support in 341 of 393 comparisons. The
candidate passed 9 of 24 supported races, matching the previously
frozen nomination/practice ridge. Race-average absolute error was
0.447 s, versus 0.444 s for the ridge. The candidate gained event
9987 and lost F1_2023_R01. None of the seven recurring failures passed.

The planned continuation test required an increased pass count and
at least one recurring failure to pass. This candidate failed that
test. R041 remains open. Fresh confirmation requires a complete
development pass. The next revisit calls for independently observed
car-specific information available by the forecast cutoff.
[Protocol](../../research/protocols/COMPOUND_OUTLAP_PACE_V32.md) ·
[Saved coverage, forecasts and replay](compound-v32-development.json)

```powershell
python research/scripts/compound_outlap_pace.py --output .cache/r041-v32-replay.json
```
