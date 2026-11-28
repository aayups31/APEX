# R047 green pit-lane duration distributions

## Accepted research scope

R047 passed fresh 2025 cross-provider confirmation for measured
green-flag pit-lane entry-to-exit duration, including service.
The frozen race-shift model scored 87 stops across five races.
Its nominal 80% interval covered 77 stops (88.5%), and each race
cleared the 50% coverage floor. Mean CRPS was **1.442 s**,
compared with **1.740 s** for the empirical pooled distribution.

| Confirmation race | Stops | Interval coverage |
|---|---:|---:|
| Australia | 11 | 81.8% |
| Bahrain | 28 | 92.9% |
| Miami | 6 | 83.3% |
| Monza | 19 | 89.5% |
| Singapore | 23 | 87.0% |

The first OpenF1 confirmation required clean peer laps inherited
from the R045 pace comparison. Australia and Miami had no eligible
stops under that filter. The direct protocol evaluates only the
lane duration observable, so it uses a conservative green clock
window around the measured pit stop and requires a native lap
link. The tested model, five races and scoring thresholds were
held fixed. The original clean-peer confirmation remains
under-supported.
[Direct protocol](../../research/protocols/PIT_LANE_CLOCK_CONFIRMATION_R047.md) ·
[Confirmed results](pit-duration-r047-direct-confirmation.json)

The research sampler exposes seeded duration draws and the central
interval. Bahrain, Australia, Miami and Monza are circuit-specific.
Singapore and unseen circuits require explicit pooled opt-in.
Confirmation replayed byte-for-byte and all eight focused tests passed.
Stationary service time, pit-loss counterfactuals, neutralized stops
and production integration require separate validation.

```python
from pathlib import Path
from random import Random
from apexsim.research.pit_duration import load_pit_duration

folder = Path("docs/verification")
duration = load_pit_duration(
    folder / "pit-duration-r047-v1.json",
    folder / "pit-duration-r047-v2.json",
    folder / "pit-duration-r047-direct-confirmation.json",
    "monza",
)
seconds = duration.sample(Random(47))
```

## First development candidate

The first distribution candidate remains unqualified. Circuit scaling
improved mean CRPS from 2.642 to 2.179 seconds across the five held-out
races. Its nominal 80% interval covered 75 of 110 stops (68.2%),
below the registered 70% minimum. Australia and Miami also missed the
50% per-race coverage floor.

| Race | Held-out stops | Coverage | Candidate CRPS | Pooled CRPS |
|---|---:|---:|---:|---:|
| Bahrain | 26 | 80.8% | 0.521 s | 0.744 s |
| Australia | 31 | 45.2% | 1.913 s | 4.941 s |
| Miami | 8 | 25.0% | 2.992 s | 1.754 s |
| Monza | 26 | 84.6% | 1.594 s | 1.895 s |
| Singapore | 19 | 84.2% | 3.877 s | 3.877 s |

The first candidate uses the training-only circuit median to scale a
shared empirical distribution. Singapore uses the pooled distribution
because it lacks five training observations. For Australia, the
candidate interval starts at 17.813 s and many observed durations are
shorter. For Miami, the interval ends at 22.048 s and six of eight
observations exceed it. These opposite shifts indicate a limitation
of using one historical center per circuit. The accepted candidate
adds declared between-race location shifts around each circuit median.

The target is pit entry-to-exit time, including service. These stops
use the green, clean-peer R045 sample. Stationary service duration
and stops under neutralization require their own evidence.
[Protocol](../../research/protocols/PIT_DURATION_DISTRIBUTIONS_R047.md) ·
[Saved results](pit-duration-r047-v1.json)

```powershell
python research/scripts/fit_pit_duration_distribution.py --output .cache/r047-distribution-replay.json
python research/scripts/confirm_direct_pit_lane_r047.py --archive .cache/r047-openf1-confirmation --output .cache/r047-direct-replay.json
```
