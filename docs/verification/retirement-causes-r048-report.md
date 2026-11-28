# R048 competing retirement hazards

R048 passed its historical research gate for two published
retirement causes. The study fitted 39 eligible races from 2022–2023
and evaluated 44 eligible races in 2024–2025. Permanent benchmark
races were excluded. Result labels come from the checksum-pinned
F1DB release and were mapped to incident, mechanical failure or
unresolved. Disqualifications were right-censored and recorded
formation-lap incidents were excluded from race-lap exposure.
[F1DB v2026.21.0](https://github.com/f1db/f1db/releases/tag/v2026.21.0) ·
[Follow-up protocol](../../research/protocols/CAUSE_HAZARD_RELIABILITY_R048.md)

| Held-out season | Incident observed / expected | Mechanical observed / expected |
|---|---:|---:|
| 2024 | 20 / 28.84 | 14 / 11.74 |
| 2025 | 33 / 34.49 | 12 / 8.21 |
| Combined | 53 / 63.34 | 26 / 19.95 |

Cause coverage was 92.3% for training and 91.9% for evaluation.
Aggregate observed-to-expected ratios were 0.84 for incidents and
1.30 for mechanical failures. Held-out negative log likelihood
improved from 650.07 to 617.25 against the homogeneous comparator.
The original first-lap split overpredicted mechanical retirements
and missed the cause coverage gate. The revised model estimates
mechanical reliability change from 2022 and 2023 only, retaining
the first-lap versus later-lap incident probabilities.
[Original candidate](retirement-causes-r048-v1.json) ·
[Qualified historical experiment](retirement-causes-r048-v2.json)

The 2024–2025 outcomes were held out of fitting and scored during
the first experiment. The revised results are repeated evaluation
of those periods. Expected counts condition on realized at-risk
exposure. The model describes retirement-triggering incidents
and failures. Incidents where the car kept running, field-level
dependencies between drivers, and new regulation eras need
separate calibration.

The opt-in sampler accepts the evaluated seasons and a one-based
lap number. It draws one of three mutually exclusive results from a
caller-controlled random stream.
The checksum-pinned archive reproduced the sealed results on replay.
All six focused tests passed, including a test that changes held-out
labels and verifies the fitted probabilities stay fixed.

```python
from pathlib import Path
from random import Random
from apexsim.research.retirement_hazards import load_retirement_hazards

model = load_retirement_hazards(Path("docs/verification/retirement-causes-r048-v2.json"))
outcome = model.for_lap(2025, 1).sample(Random(48))
```

```powershell
python research/scripts/fit_cause_hazards.py --reliability-trend --archive .cache/r048-f1db-v2026.21.0.zip --output .cache/r048-hazard-replay.json
```
