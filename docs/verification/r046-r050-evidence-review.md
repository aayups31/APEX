# R046–R050 evidence review

| Milestone | Status | Current evidence and remaining gate |
|---|---|---|
| R046 | Blocked | The project has no accepted calibrated race kernel. Driver lap-time residuals require matched predictions from such a kernel and held-out event evaluation. |
| R047 | In progress | A declared race-level shift model passed the development gate. The frozen five-race confirmation awaits valid lap and pit clocks. |
| R048 | In progress | A retirement baseline ran on five held-out races. Cause-specific incident and mechanical-failure models require sourced labels. |
| R049 | In progress | An archive audit found comparable pre, under, and post-neutralization snapshots for two of eight episodes. Gap compression and restart parameters still need calibrated replay and invariant checks. |
| R050 | In progress | The archive audit supplies green timing-line order proxies. Dirty-air, DRS and pass effects still need matched trajectory exposure and held-out model tests. |

## R047 distribution and confirmation

The race-shift model reduced mean CRPS from 2.642 to 2.213 seconds
against the pooled comparator. The nominal 80% interval covered
98 of 110 stops (89.1%). Every event met the 50% coverage floor.
The multiplier choice was made after the first development study.

FastF1 failed to obtain lap timing for all five registered 2025 races.
The official live-timing index for Monza returned HTTP 401 on a direct
probe, and no complete confirmation archive was accepted. The FIA
publishes pit summaries that could be reconciled with lap and
race-control timing in a new source-validation protocol.
[Development results](pit-duration-r047-v2.json) ·
[Confirmation protocol](../../research/protocols/PIT_DURATION_RACE_SHIFT_R047.md) ·
[FIA Monza pit timing report](https://www.fia.com/sites/default/files/2025_16_ita_f1_r0_timing_racepitstopsummary_v01.pdf)

## R048–R050 native evidence

Nine verified FastF1 race archives supply the source audit. The
four 2023 races train the all-cause retirement model. The five
held-out 2024 races record seven retirements. The constant model
expects 21.8 retirements conditional on realized exposure and has
held-out negative log likelihood 60.44. Splitting out first-lap
hazard raises it to 61.76. Neither result substantiates a calibrated
cause-specific hazard. The source classification records retirement
without reliably identifying why it happened.

The two matched race-control snapshots cover one SC episode
in Miami 2024 and one VSC episode in Singapore 2023. Snapshots use
the same nonpitting drivers on complete laps before, during and
after neutralization. Their field spans are diagnostic and do
not identify an individual chase or restart rule.

The clean-lap audit found 3,213 adjacent timing-line pairs within
two seconds across consecutive race laps, and 172 subsequently
reversed their order. Adjacency is among retained cars. The
reversal count is a proxy for position changes and the archive
inventory also records per-driver car and position tables.
[Retirement protocol](../../research/protocols/RETIREMENT_HAZARD_R048.md) ·
[Source audit](race-model-source-audit.json)

```powershell
python research/scripts/fit_pit_duration_race_shift.py --output .cache/r047-v2-replay.json
python research/scripts/confirm_pit_duration_r047.py --output .cache/r047-confirmation.json
python research/scripts/audit_race_model_sources.py --output .cache/r048-r050-source-replay.json
```
