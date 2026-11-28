# R041 external tyre telemetry and masked reconstruction

R041 remains open. The first external test used 20 real driving
runs with measured tread temperatures. The masked estimator missed
its cross-session acceptance gate. Providing one measured starting
temperature materially reduced the error. The experiment evaluated
temperature reconstruction on an autonomous VW Golf at Thunderhill.
[Registered protocol](../../research/protocols/COMPOUND_EXTERNAL_THERMAL_V34.md) ·
[Sealed results](compound-v34-external-thermal.json) ·
[Stanford dataset](https://doi.org/10.25740/hh613qz0317)

## External data qualification

| Source | Verified finding | Suitable scope |
|---|---|---|
| BETTY Monza | The public plot for run 48 contains 46,925 temperatures per wheel over 469.385 s. It contains only those four plotted channels. The data page points to a placeholder and the exact MCAP snippet linked from the public demo timed out from this environment. | Temperature ranges and dynamics. A synchronized raw subset would enable the observer and lap coverage checks. |
| Constructor Yas Marina | BoxBoxAI publishes a derived CSV with 4,064 rows over 81.259 s. All 24 wheel channels for centre, inner and outer surface temperatures, TPMS temperature, absolute pressure and wheel load are populated and vary. The CSV has one lap index, zero recorded lap times and a constant zero available-fuel channel. | Sensor and short-interval dynamics checks. The raw recordings and their reuse terms need confirmation from the provider. |
| Stanford Thunderhill | Acquired 20 unique CSV runs with public download access under CC BY-SA 4.0. Two October files were byte-identical copies and were excluded. The logs span about 63–232 s and provide four tread temperatures, matched controls and GPS. At most two large track-progress wraps appeared per file. | Independent session transfer for masked tread-temperature reconstruction. The available logs lack a verified three-lap forecast window with established stint identity. |
| FSAE Tire Test Consortium | Controlled force, slip, load and temperature data is available through member schools. Its participant agreement limits use to school activities and restricts redistribution and commercial use. | Force and thermal identification within authorized use. |
| TUM GPTireUKF | The Apache-2.0 repository implements vehicle speed and sideslip estimation with tyre-model inputs that can include temperature. The experiment logs named by the examples were absent from the checked repository tree. | Design reference for uncertainty and measurement updates. |

The immutable source snapshots were checked against the documented
fields. The BETTY plot is not a join to a Formula 1 Monza session.
The BoxBoxAI CSV is an aligned export and its 50 Hz row grid does
not establish the native sensor rates. The TPMS temperatures and
tread temperatures remain separate observables. The BoxBoxAI schema
expresses absolute pressure in mbar and does not state a unit for
the published wheel-load fields.
[BETTY paper](https://arxiv.org/abs/2505.07266) ·
[BETTY plotted source](https://raw.githubusercontent.com/PITT-MIT-IAC/betty-dataset/1bbd86df398deb53821dbe323657f59192d92de3/static/js/plotting/grun48/grun48.js) ·
[Constructor recording descriptions](https://github.com/azimsh3r/BoxBoxAI/blob/main/driving-data/README.md) ·
[Constructor sample](https://raw.githubusercontent.com/azimsh3r/BoxBoxAI/78b7702bf85f5911605acdd06acb79755569e871/web/public/session_summary_good.csv) ·
[FSAE participant agreement](https://www.millikenresearch.com/FSAE_TTC_agreement.pdf) ·
[GPTireUKF](https://github.com/TUMFTM/GPTireUKF)

BETTY plot SHA-256 `24fd8a04763d094b31dc7d9b334bd09e632351f01e89c73461c12c19d77323a4`.
Constructor CSV SHA-256 `3651209ebe4732a106ef1c90c99392f5bb84d294051793e4d299f9bbe5438e16`.
Each Stanford file was checked against its published size and SHA-1
and then recorded with a SHA-256 digest for offline replays.
[Stanford publication metadata](https://purl.stanford.edu/hh613qz0317.json)

## Measured temperature results

The two directions hold out all runs from one collection session.
Inputs were causal speed, throttle, RPM, binary brake and horizontal
position. Only the supervised target used measured tyre temperatures.
The two-node heat model uses APEX’s existing fixed thermal parameters
and a declared kinematic heating proxy. The fitted coefficients map
its temperatures and the observed controls to measured tread
temperature. The fit does not identify heat capacities or physical
pressure, wear and grip states.

| Equal-run MAE | October → November, 12 runs | November → October, 8 runs |
|---|---:|---:|
| Time-only control | 14.75 °C | 14.62 °C |
| Public-compatible controls | 14.45 °C | 14.94 °C |
| Two-node heat readout | 13.72 °C | 14.11 °C |
| Hybrid, all tyre sensors masked | 14.11 °C | 14.90 °C |
| Hold measured starting temperature constant | 5.84 °C | 5.86 °C |
| Hybrid with measured starting temperature | 3.62 °C | 3.34 °C |

The hybrid beat time-only in five of 12 November runs and three
of eight October runs. The two-node readout lowered aggregate error
in both directions and beat time-only in five of 12 and five of eight
runs. The registered gate failed. The measured-initialization check
used the first eligible observation per segment. It beat holding the
same value constant on the same evaluation samples in both transfer
directions. That comparison was added after the first transfer results.

The result makes initial tyre temperature a concrete variable to
investigate. A useful next data request is a small telemetry-only
subset covering warm-up, pit transitions and multiple complete
consecutive laps. It needs timestamped temperatures, pressure, controls,
position, ambient or track temperature, lap clocks, compound and tyre-set
identifiers, and permission to use the measurements and report aggregates.
That would support testing whether measured starting state improves
three-lap pace forecasts, then whether a masked observer can recover
enough of that gain across independent runs. The game UDP channels
also support a controlled simulation experiment with the same masks.
[EA F1 25 UDP specification](https://forums.ea.com/blog/f1-games-game-info-hub-en/ea-sports%E2%84%A2-f1%C2%AE25-2026-season-pack-udp-specification/12187347)

## R041 fuel labels

The existing full-range fuel audit marks 174 of 393 windows as
sensitive in at least one of the two crossover definitions. Among
the seven recurring failures, 47 of 131 windows are sensitive. The
frozen ridge still gets 81 of 492 fuel-stable decisions wrong across
all races, including 29 of 180 in the seven recurring races. V33
gets 82 and 28 wrong, respectively. This stratification uses
the sealed v24 label audit and saved predictions. Official labels,
acceptance gates and fresh confirmation remain frozen.
[Fuel sensitivity evidence](compound-v24-residual-audit.json) ·
[Frozen ridge](compound-v24-development.json) ·
[V33 forecasts](compound-v33-development.json)

## Reproduce

```powershell
python research/scripts/archive_stanford_tyre_runs.py --archive .cache/r041-stanford-v3
python research/scripts/compound_external_thermal.py --archive .cache/r041-stanford-v3 --output .cache/r041-v34-external-replay.json
python -m pytest -q apex_engine/tests/test_external_tyre_thermal.py apex_engine/tests/test_tyre_thermal.py
```

Two masked runs reproduced the report bytes. The external telemetry
bytes stay in the ignored cache.
