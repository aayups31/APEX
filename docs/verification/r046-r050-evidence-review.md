# R046–R050 evidence review

| Milestone | Status | Current evidence and remaining gate |
|---|---|---|
| R046 | Research gate passed | The separately calibrated clean-green one-lap model passed five held-out races. Integrated race-kernel calibration remains pending. [R046 report](lap-residuals-r046-report.md) |
| R047 | Research gate passed | The direct green pit-lane confirmation passed on 87 stops across five races. The earlier clean-peer confirmation had too few supported races. [R047 report](pit-duration-r047-report.md) |
| R048 | Research gate passed | Published cause labels supported an accepted historical competing-risk model. Full-field incident calibration remains open. [R048 report](retirement-causes-r048-report.md) |
| R049 | Research gate passed | Per-car SC and VSC timing-line replay passed on 19 held-out episodes. [R049 report](neutralized-gaps-r049-report.md) |
| R050 | Research gate passed | Corroborated passes and signed gaps passed five held-out races. Conditional following and DRS sector adjustments passed a separate three-race confirmation. [R050 report](green-traffic-r050-report.md) |

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

OpenF1 supplied all five archives. Under the frozen substitution
protocol, Bahrain had 28 supported stops, Monza 18 and Singapore 23.
Australia and Miami had zero after clock, green-period and peer
checks. The minimum-support gate failed before scoring the panel.
[Source substitution protocol](../../research/protocols/PIT_DURATION_OPENF1_R047.md) ·
[OpenF1 confirmation evidence](pit-duration-r047-openf1-confirmation.json)

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

The R049 extension added the already opened OpenF1 archives.
On ten SC episodes, the per-mode model achieved 9.02 s MAE for field
span during neutralization and 3.75 s for the first matched green lap.
Preserving the original span gave 22.69 s and 32.83 s respectively.
No VSC episode had enough independent same-mode training races to score.
[R049 protocol](../../research/protocols/NEUTRALIZATION_SPAN_R049.md) ·
[Field-span evaluation](r049-neutralization-span.json)

The R050 archive join supplied 1,504 training and 1,709 held-out
comparisons with usable DRS histories. Adding DRS worsened the Brier
score in four of five held-out races and did not improve the
equally race-weighted score. The outcome remains a timing-line proxy.
[R050 protocol](../../research/protocols/TRAFFIC_DRS_REPLAY_R050.md) ·
[Held-out DRS results](r050-drs-association.json)

The subsequent R050 replay joined the pass log to signed timing-line
gaps on 1,390 held-out transitions. The sector confirmation qualified the
close-following and DRS pace terms on 211 matched contrasts. Both
scoped calibrations are available in the offline research replay.
[R050 closure report](green-traffic-r050-report.md)

```powershell
python research/scripts/fit_pit_duration_race_shift.py --output .cache/r047-v2-replay.json
python research/scripts/confirm_pit_duration_r047.py --output .cache/r047-confirmation.json
python research/scripts/audit_race_model_sources.py --output .cache/r048-r050-source-replay.json
python research/scripts/confirm_pit_duration_openf1.py --archive .cache/r047-openf1-confirmation --output .cache/r047-openf1-replay.json
python research/scripts/fit_neutralization_span.py --output .cache/r049-span-replay.json
python research/scripts/fit_traffic_drs_proxy.py --output .cache/r050-drs-replay.json
```
