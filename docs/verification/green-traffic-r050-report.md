# R050 green-flag traffic calibration

R050 passed the offline research gate. APEX can forecast next-lap
signed gaps and corroborated passes for close adjacent pairs. It can
also apply separate historical sector-time adjustments for close
following and observed DRS. The studies cover clean, green,
pre-2026 racing. [Gap and pass protocol](../../research/protocols/GREEN_TRAFFIC_R050.md) ·
[Sector protocol](../../research/protocols/SECTOR_TRAFFIC_R050.md)

## Gap and pass replay

The model was fit on four 2023 races and scored on five 2024 races.
It retained 1,390 held-out transitions, including 67 timing-line
reversals. The OpenF1 pass log corroborated all 67 in the expected
direction. Four logged exchanges failed to produce an order change
at the next line. The model forecasts passes that last to that line.
OpenF1's log can contain pit and penalty position changes, so replay
requires consecutive accurate green nonpit laps and matching timing
order. The two providers share upstream timing provenance.
[OpenF1 overtake fields and limitations](https://openf1.org/docs/#overtakes) ·
[Sealed gap and pass evidence](r050-green-traffic.json)

| Held-out metric | Model | Baseline |
|---|---:|---:|
| Gap MAE versus persistence | 0.350 s | 0.381 s |
| Gap MAE versus unshrunk pace extrapolation | 0.350 s | 0.397 s |
| Corroborated-pass Brier score | 0.04240 | 0.04588 |
| Corroborated-pass log loss | 0.15616 | 0.19325 |

The gap model beat persistence in all five races and the pass model
expected 60.4 passes against 67 observed. Development race validation
selected the gap and relative pace classifier. Adding completed-lap
DRS slightly worsened held-out Brier score and log loss. The separate
sector model uses DRS state within the measured sector.

## Following pace and DRS

The initial full-lap comparison failed support, with only one
following and two DRS matches on the 2024 panel. The sector follow-up
compared clean sectors within driver, circuit, tyre stint and sector,
with a limit on the difference in matched tyre ages. Frozen 2023
coefficients reproduced the expected direction for close following in
five of five 2024 races and for DRS in four of five. Both directions
replicated in all three added 2022 confirmation races.
[Sealed sector evidence](r050-sector-traffic.json)

| Term | Fitted adjustment | Confirmation matches | Confirmation MAE, model / zero effect |
|---|---:|---:|---:|
| DRS-closed sector within 1 s versus closed at 2–4 s | +0.254 s | 130 | 0.405 / 0.474 s |
| DRS-open versus closed sector, both within 1 s | −0.307 s | 134 | 0.475 / 0.606 s |

These are observational timing adjustments. The measured effects
vary by race, and tyre ages can differ within the allowed matching
window. The estimates use timing-line neighbors as a proxy for traffic
exposure. They leave physical downforce, the integrated full-field
kernel and the 2026 rules outside the qualified scope.

## Run the replay

```python
from pathlib import Path
from apexsim.research.green_traffic import (
    load_green_traffic_replay,
    load_sector_traffic_calibration,
)

evidence = Path("docs/verification")
pair = load_green_traffic_replay(evidence / "r050-green-traffic.json")
forecast = pair.forecast(gap_s=0.7, pace_delta_s=-0.2)
sector = load_sector_traffic_calibration(evidence / "r050-sector-traffic.json")
time_adjustment_s = sector.adjustment(gap_s=0.7, drs_open=True)
```

Use the verified FastF1 archive layout in the scripts and the frozen
OpenF1 archive for exact replay. Two local runs reproduced both
committed evidence files byte for byte. Raw provider files stay in
the cache. The pass archive can be acquired against the public API,
whose responses may change over time.

```powershell
python research/scripts/archive_r050_overtakes.py --archive .cache/r050-openf1
python research/scripts/fit_green_traffic_r050.py --pass-archive .cache/r050-openf1 --output .cache/r050-green-traffic-replay.json
python research/scripts/fit_sector_traffic_r050.py --output .cache/r050-sector-traffic-replay.json
python -m pytest -q apex_engine/tests/test_green_traffic.py
```
