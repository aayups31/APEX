# R047 green pit-lane duration distributions

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

The candidate uses the training-only circuit median to scale a
shared empirical distribution. Singapore uses the pooled distribution
because it lacks five training observations. For Australia, the
candidate interval starts at 17.813 s and many observed durations are
shorter. For Miami, the interval ends at 22.048 s and six of eight
observations exceed it. These opposite shifts indicate a limitation
of using one historical center per circuit. The next test should
use additional earlier same-circuit races to estimate between-race
dispersion, keeping the 2024 evaluation out of the fit.

The target is pit entry-to-exit time, including service. These stops
use the green, clean-peer R045 sample. Stationary service duration
and stops under neutralization require their own evidence.
[Protocol](../../research/protocols/PIT_DURATION_DISTRIBUTIONS_R047.md) ·
[Saved results](pit-duration-r047-v1.json)

```powershell
python research/scripts/fit_pit_duration_distribution.py --output .cache/r047-distribution-replay.json
```
