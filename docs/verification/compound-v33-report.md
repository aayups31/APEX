# R041 sector traffic adjustment and tyre-state data search

R041 remains open. The sector-traffic candidate passed eight of 24
supported development races. The frozen nomination/practice ridge
passed nine. None of the seven recurring failures passed in this
experiment. The candidate lost 2025 Abu Dhabi when recall for one
crossover definition fell below the existing 50% floor.
[Registered protocol](../../research/protocols/COMPOUND_SECTOR_PACE_V33.md) ·
[Sealed development evidence](compound-v33-development.json)

| Forecast | Races passing | Race-averaged absolute contrast error |
|---|---:|---:|
| Frozen nomination/practice ridge | 9 / 24 | 0.444004 s |
| Ridge with sector availability | 9 / 24 | 0.445757 s |
| Ridge with sector time adjustments and availability | 8 / 24 | 0.443703 s |

The experiment kept all 393 comparisons and excluded the entire
test race from each fit. The traffic terms came from three 2022 races
outside the R041 cohort. They were +0.317 s for the close-following
sector comparison and −0.5665 s for DRS within the close band.
Only sector observations ending by the forecast cutoff were used.
Of 393 cases, 361 had at least one supported sector and 286 had
a close-following or DRS observation. The seven recurring failure
races had support in 123 of 131 cases, including 102 with a
close-following or DRS observation. This method had broad coverage
and missed the continuation gate. Fresh confirmation remains sealed.
[R050 sector evidence](r050-sector-traffic.json)

## Other potential inputs

The public archives checked provide timing, compound and stint
information, car telemetry, and weather. The FIA scrutineering records
report that temperature and pressure checks occurred. I found no
joinable series of individual per-wheel temperature or pressure
measurements covering the recurring failures in these sources.
Formula 1's broadcast tyre performance graphics are estimates
computed from timing, telemetry and other data. The description
provides no archive of measured tyre-state observations.
[FastF1 data reference](https://docs.fastf1.dev/data_reference/index.html) ·
[F1Archive data reference](https://f1archive.org/docs) ·
[2024 curated dataset](https://zenodo.org/records/20061496) ·
[Example FIA scrutineering report](https://www.fia.com/sites/default/files/decision-document/2023%20United%20States%20Grand%20Prix%20-%20Race%20scrutineering.pdf) ·
[Formula 1 tyre performance graphic](https://www.formula1.com/en/latest/article/explaining-the-new-tyre-performance-graphics-seen-on-tv.21CVJlHg0St8zrzaaVbU4L)

The radio screen read the text and timestamp columns for 14,681
archived clips. It matched race, date and car number, and screened
the current stint from its first recorded lap completion or ten minutes before
cutoff, whichever was later. It required clips to start at least
30 seconds before the cutoff. Six of the 131 target windows had
any clip. One had a tyre-related keyword that also matched the
symptom pattern. OpenF1 metadata gave the same six-window coverage.
The transcript match is a keyword screen with no independent audio
or predictive verification. Coverage is too sparse for this input
to test the full group of recurring failures.
[Radio transcript dataset](https://huggingface.co/datasets/MikCil/f1-team-radio/tree/a0b99e1a325d92d63b574541a24902a660a352ea) ·
[OpenF1 radio schema](https://openf1.org/docs/#team-radio) ·
[Sealed radio coverage](compound-radio-support.json)

The next candidate should carry car-specific information about tyre
state available before the forecast. Check timestamped per-wheel
temperature or pressure, or another independently verified signal
with race, driver and stint identifiers. First measure its coverage
on the seven recurring failures and its incremental value against
the frozen ridge. Keep the existing race gates for qualification.

## Reproduce

Two runs from the same verified lap and car archives reproduced
the v33 evidence byte for byte. The audit recomputed all 393
forecasts' metrics and both crossover gates per supported race.

```powershell
python research/scripts/compound_sector_pace.py --output .cache/r041-v33-replay.json
python research/scripts/audit_compound_radio_support.py --transcripts .cache/r041-radio-text.json --output .cache/r041-radio-replay.json
python -m pytest -q apex_engine/tests/test_compound_sector_pace.py apex_engine/tests/test_green_traffic.py
```

For the radio replay, project `id`, `racing_number`, `race_id`,
`session_date`, `message_timestamp` and `transcription` from the five
Parquet shards in the pinned revision. Concatenate in filename and
row order and serialize the list with `json.dumps(..., ensure_ascii=False,
sort_keys=True)` in UTF-8. Raw transcript text and audio are excluded
from the repository.
