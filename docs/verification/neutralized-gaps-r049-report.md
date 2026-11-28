# R049 per-car neutralization and restart gaps

R049 passed its matched timing-line research gate for Safety Car
and Virtual Safety Car. Each evaluated race was excluded from its
fit. The comparison uses the same nonpitting cars before, during,
and after each episode. Observed order changes remain in the score.
[Protocol](../../research/protocols/PER_CAR_RESTART_R049.md) ·
[Per-car results](r049-per-car-gaps.json)

| Mode | Held-out races / episodes | During MAE, model / persistence | First green lap MAE, model / persistence |
|---|---:|---:|---:|
| Safety Car | 6 / 8 | 6.955 / 25.049 s | 3.406 / 33.660 s |
| Virtual Safety Car | 9 / 11 | 1.282 / 6.308 s | 1.978 / 1.978 s |

The model scales each car's cumulative gap to the matched cohort's
leader. Safety Car compresses those gaps. VSC expands the time gap
in the neutralized snapshot and explicitly restores the original
gap for the first green lap. The replay keeps a zero leader gap and
preserves the modeled running order. It returns green at the release
clock. The first green snapshot models the first matched complete lap.
The archive replay reproduced the fitted factors and forecasts.
All six focused tests passed, including the release boundary and
running-order invariants.

```python
from pathlib import Path
from apexsim.research.neutralized_gaps import load_neutralization_gaps
from apexsim.sim_core.types import FlagState

model = load_neutralization_gaps(Path("docs/verification/r049-per-car-gaps.json"))
replay = model.replay(FlagState.SAFETY_CAR, (0.0, 3.0, 8.0), start_s=250, release_s=410)
```

This replay is conditional on knowing the episode clocks and
the nonpitting cohort. It evaluates timing-line snapshots with
partially observed fields. Full-field deployment timing, pit and
lapped-car behavior, continuous trajectory dynamics and production
integration need separate verification.

```powershell
python research/scripts/fit_neutralized_car_gaps.py --output .cache/r049-per-car-replay.json
python -m pytest -q apex_engine/tests/test_neutralized_gaps.py
```
