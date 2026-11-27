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

## Wider clock training

Using all qualifying green pit clocks increased training from 68 to 74
stops. The extra records came from Bahrain and Monza. Australia and
Singapore still had just two and three qualifying training stops.
Anchoring the two proxy components to measured pit-lane segments made
race-averaged total error 3.649 s and improved zero races against the
pooled baseline. R045 remains open. The next calibration should acquire
more earlier green training races at the underrepresented circuits or
introduce event-independent circuit geometry features before retesting.
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
```
