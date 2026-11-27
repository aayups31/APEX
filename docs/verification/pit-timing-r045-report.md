# R045 held-out pit timing

R045 passed its registered research gate with expanded training coverage.
Adding 25 supported stops from Australia, Miami and Singapore in 2022
increased training from 68 to 93 stops. The evaluation remained the
same 110 stops across five 2024 races. The 2023 Miami archive returned
no lap timing on two attempts. The source exclusion was recorded
before any added stops were scored.

| Held-out race | Expanded circuit model total MAE | Original pooled MAE | Expanded pooled MAE |
|---|---:|---:|---:|
| Bahrain | 1.114 s | 1.403 s | 1.152 s |
| Australia | 2.394 s | 4.308 s | 3.796 s |
| Miami | 2.825 s | 4.145 s | 3.704 s |
| Monza | 2.392 s | 2.682 s | 3.230 s |
| Singapore | 5.748 s | 5.160 s | 5.748 s |
| Race average | 2.895 s | 3.540 s | 3.526 s |

The expanded model improved four races against the original pooled
comparator. Singapore had four training stops, below the five-stop
circuit minimum. Its pooled error increased. The new calibration is
an opt-in interface for the research strategy model, and circuits
without their own calibration require explicit fallback opt-in.
Measured lane time is an informational output. The strategy model
uses the incremental pit-loss proxy and allocates its joint median
across the inlap and outlap using the shares of their marginal medians.
The resulting inlap and outlap MAEs were 0.364 and 1.049 s at Bahrain,
2.359 and 0.717 s at Australia, 0.813 and 2.209 s at Miami, and 0.439
and 2.241 s at Monza. The strategy adapter preserves the qualified
total and charges it exactly once across an isolated stop.
[Expanded protocol](../../research/protocols/PIT_TIMING_EXPANDED_R045.md) ·
[Qualified calibration and scores](pit-timing-r045-v3.json)

```python
from pathlib import Path
from apexsim.research.fienia_strategy import PaperStrategyModel, PaperStrategyParameters
from apexsim.research.pit_timing import load_pit_timing

timing = load_pit_timing(Path("docs/verification/pit-timing-r045-v3.json"), "monza")
model = PaperStrategyModel(timing.apply(PaperStrategyParameters()))
```

The seal and scores reproduced byte-for-byte from the three verified
native archives. The focused suite passed nine tests, including a
training/evaluation overlap rejection and a real inlap/outlap transition
through the research model. The 2024 outcomes were held out of all fits
and used in earlier R045 studies. The proxy includes residual driving
and tyre effects from the lap comparisons. Further confirmation on
fresh events is needed for a production or counterfactual claim.
[Implementation CI](https://github.com/aayups31/APEX/actions/runs/46083926600)

## First calibration

The first circuit-median calibration missed the acceptance gate. It
scored 110 supported stops in five 2024 races after training on 68
supported stops in four 2023 races. Research and production maturity
remain at R1 and R0.

| Held-out race | Stops | Circuit model total MAE | Pooled MAE |
|---|---:|---:|---:|
| Bahrain | 26 | 1.114 s | 1.403 s |
| Australia | 31 | 4.308 s | 4.308 s |
| Miami | 8 | 4.145 s | 4.145 s |
| Monza | 26 | 2.392 s | 2.682 s |
| Singapore | 19 | 5.160 s | 5.160 s |
| Race average | | 3.424 s | 3.540 s |

The model improved two races. The registered test requires three.
Australia and Singapore supplied two and three supported 2023 stops
respectively, so both fell back to the pooled estimate. Miami had no
training race. Pit entry-to-exit time is measured. Incremental lap
penalties use a retrospective clean-peer timing proxy.
[Protocol](../../research/protocols/PIT_TIMING_R045.md) ·
[Full evidence](pit-timing-r045-v1.json)

## Wider clock training

Using all qualifying green pit clocks increased training from 68 to 74
stops. The extra records came from Bahrain and Monza. Australia and
Singapore still had just two and three qualifying training stops.
Anchoring the two proxy components to measured pit-lane segments made
race-averaged total error 3.649 s and improved zero races against the
pooled baseline.
[Wider-clock protocol](../../research/protocols/PIT_TIMING_CLOCKS_R045.md) ·
[Wider-clock evidence](pit-timing-r045-v2.json)

This also suggests a targeted R041 investigation. The absolute pit-exit
clock and the completed outlap's pace relative to clean peers can give
information about early-stint recovery. First join both signals to the
subject's existing forecast clock, keeping peer laps only if they had
already ended. Report independent coverage on the seven persistent
failures before evaluating a candidate. This is a possible warm-up
proxy whose predictive value is untested.

```powershell
python research/scripts/calibrate_pit_timing.py --output .cache/r045-replay.json
python research/scripts/calibrate_pit_clocks.py --output .cache/r045-clock-replay.json
python research/scripts/calibrate_pit_expanded.py --output .cache/r045-expanded-replay.json
```
