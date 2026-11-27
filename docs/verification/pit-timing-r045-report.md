# R045 held-out pit timing

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

```powershell
python research/scripts/calibrate_pit_timing.py --output .cache/r045-replay.json
```
