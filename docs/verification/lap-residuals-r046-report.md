# R046 clean-green next-lap residuals

R046 passed the restricted one-step research gate on 3,737 laps
across five held-out races. The point model is calibrated on 2,382
windows in four 2023 races. The empirical error distributions use
forecasts built by excluding each calibration race in turn. The five
2024 races supply evaluation only.
[Registered protocol](../../research/protocols/LAP_RESIDUALS_R046.md) ·
[Sealed checkpoints and predictions](lap-residuals-r046-v1.json)

| Metric | Calibrated one-lap model | Last-lap persistence |
|---|---:|---:|
| Race-averaged point MAE | 0.332 s | 0.347 s |
| Race-averaged CRPS | 0.258 s | 0.271 s |

The model's nominal 80% intervals covered 81.5% of held-out laps.
Per-race coverage ranged from 74.1% to 87.1%. A driver-specific
distribution contributed to 3,447 of 3,737 forecasts. Other drivers
use the pooled residuals. Window overlap and repeated drivers
create dependencies between observations.

The research interface produces a point forecast and seeded
pace draws after three completed clean laps on the same stint.
It reads residuals from the training calibration only.
All 17 focused tests passed, including checkpoint replay, seeded
draws, fallback for unknown drivers and an independent CRPS calculation.

```python
from pathlib import Path
from random import Random
from apexsim.research.lap_residuals import load_lap_residuals

model = load_lap_residuals(Path("docs/verification/lap-residuals-r046-v1.json"))
forecast = model.forecast("16", (92.1, 91.8, 92.0), tyre_age=8, lap=12, compound="MEDIUM")
simulated_next_lap_s = forecast.sample(Random(46))
```

This acceptance covers clean-green, same-stint, one-step forecasts
conditional on retrospective source quality flags. Integrated race
kernel residual calibration remains dependent on an accepted
full-field lap model. Pit laps, neutralizations, wet tyres and
recursive simulation are outside the evaluated scope.

```powershell
python research/scripts/fit_lap_residuals.py --output .cache/r046-residuals-replay.json
python -m pytest -q apex_engine/tests/test_lap_residuals.py
```
