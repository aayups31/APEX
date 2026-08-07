# Data Plan Without F1 25

## Data-source roles

### FastF1

Use for historical sessions, laps and per-lap telemetry including speed, RPM, gear, throttle, brake, DRS and GPS-like position. FastF1 supports session loading by event and session identifier, caching, lap selection and telemetry access.

Best role in APEX:

- practice and qualifying lap replay;
- track reconstruction;
- action/speed alignment;
- lap/stint features;
- historical validation.

### OpenF1

Use for historical data from 2023 onward and, only if needed later, licensed/paid real-time access. Its endpoint set includes car data, laps, location, intervals, overtakes, pit, position, race control, session results, starting grid, stints and weather. Car data is sampled at approximately 3.7 Hz.

Best role in APEX:

- full-field race timelines;
- independent joins across car/location/weather/stint/pit/race-control streams;
- race-state reconstruction;
- live-mode prototyping after historical validation.

### Jolpica F1

Use for schedules, circuits, drivers, constructors, results, standings, laps and pit stops where high-frequency telemetry is not required. Set a descriptive custom user agent and honor pagination/rate limits.

Best role in APEX:

- event catalog;
- race metadata;
- historical results and classification;
- cross-checking session identity.

### Synthetic generator

Keep the existing generator. Synthetic data is the only source where causal rules and hidden state are known.

Best role in APEX:

- invariant tests;
- leakage tests;
- identifiability experiments;
- planner tests;
- controlled weather/tyre/traffic scenarios.

## Source-of-truth matrix

| Entity | Primary source | Secondary check | Notes |
|---|---|---|---|
| Event/session identity | FastF1/OpenF1 | Jolpica | Freeze source IDs in manifest |
| Lap timing | FastF1/OpenF1 | Jolpica | Normalize time zones and session time |
| Car controls/speed | FastF1/OpenF1 | none | Broadcast-level, not team sensor rate |
| XY/location | FastF1/OpenF1 | track reconstruction | Smooth and map-match |
| Weather | OpenF1/FastF1 | none | As-of join, never row-number join |
| Tyre compound/stint | OpenF1/FastF1 | lap timing | Validate pit boundaries |
| Pit events | OpenF1/Jolpica | FastF1 laps | Separate lane time and stationary time if possible |
| Race control | OpenF1/FastF1 | official event documents | Preserve event-time order |
| Final classification | Jolpica/OpenF1 | FastF1 | Use only for evaluation labels |

## Required canonical tables

### sessions

```text
session_id, season, round, event, session_type, start_utc,
track_id, source_ids, ruleset_version
```

### telemetry

```text
session_id, driver_id, timestamp_utc, session_time_s,
lap_number, lap_distance_m, x_m, y_m,
speed_mps, acceleration_mps2,
throttle, brake, gear, rpm, drs,
source_quality_flags
```

### laps

```text
session_id, driver_id, lap_number, lap_time_s,
sector times, valid/accurate flags, track status,
stint_id, compound, tyre_age_laps, pit-in/out
```

### stints

```text
session_id, driver_id, stint_id, start_lap, end_lap,
compound, reported tyre age, inferred degradation features
```

### weather

```text
session_id, timestamp_utc, air/track temperature,
rainfall, humidity, pressure, wind speed/direction
```

### race_control

```text
session_id, timestamp_utc, category, flag, scope,
message, lap_number, sector/location
```

### track_map

```text
track_id, map_version, s_m, x_m, y_m,
curvature_1pm, elevation_m?, width_m?,
drs_zone, pit_lane, provenance and uncertainty
```

## Alignment procedure

1. retain original timestamps and source rows;
2. convert all timestamps to UTC plus session-relative seconds;
3. deduplicate within each source stream;
4. mark source sampling gaps;
5. join by nearest prior/nearest time only with explicit tolerance;
6. never interpolate categorical race-control or pit state across unknown gaps;
7. resample continuous telemetry after joins;
8. derive acceleration after smoothing speed, not before;
9. create lap boundaries from source lap events, not cumulative-distance guesses where source laps exist;
10. save an alignment report with match rates and maximum join error.

## Track reconstruction procedure

1. select accurate, non-pit laps;
2. normalize each lap to lap distance;
3. remove obvious location outliers;
4. align laps in distance bins;
5. median aggregate XY across laps/drivers;
6. smooth the reference line;
7. compute heading and signed curvature;
8. check closure error and length stability;
9. mark DRS and pit zones from source events;
10. store uncertainty per segment.

The delivered `TrackMap.from_canonical_telemetry` is a transparent starting implementation, not the final map-matching method.

## Split policy

Never random-split telemetry frames.

Recommended hierarchy:

- test tracks held out for cross-track generalization;
- test events held out for temporal generalization;
- test drivers held out for policy generalization;
- entire sessions held out at minimum;
- no lap from the same session in more than one split.

## Dataset versions

```text
apex-public-v0  one event, debugging only
apex-public-v1  3 tracks × several sessions, single-car replay
apex-public-v2  10+ tracks, driver/session holdouts
apex-race-v1    full-field race events with pit/flag/weather joins
```

## Raw-data policy

Do not commit bulk downloaded timing or telemetry data. Commit:

- downloader code;
- source manifest;
- query parameters;
- timestamps;
- hashes;
- schema/quality summaries;
- small synthetic fixtures;
- user-generated derived model artifacts only where permitted.

## Official references

- FastF1 documentation: https://docs.fastf1.dev/ and https://theoehrly-fast-f1.mintlify.app/
- OpenF1 documentation: https://openf1.org/docs/
- Jolpica F1 documentation: https://github.com/jolpica/jolpica-f1/tree/main/docs
- FIA regulations portal: https://www.fia.com/regulation/category/110
- Formula 1 brand/data guidelines: https://www.formula1.com/en/information/guidelines.4EOKE9RRqevL4niTK9kWyt

Review source terms at download time. They may change.
