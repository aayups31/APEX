# R024 tyre-energy proxy dataset card

This is a dedicated canonical research dataset, `apex-tyre-energy-proxy-v1`,
from verified FastF1 2024 Bahrain/Australia/Miami/Monza/Singapore race archives.
Drivers 4 and 44 were fixed before proxy outcomes. The sealed R021 mask selects
retrospective clean dry laps; every native car row is retained as a proxy sample
or receives an exclusion reason. This is separate from the legacy dense CSV and
the R019 qualifying corpus. Permanent benchmarks remain excluded.

Public telemetry supplies speed, throttle, binary brake and position coordinates.
The provider can reconstruct those values upstream. Measured wheel forces, slip
and tyre energy are absent; their twelve canonical fields remain null UNKNOWN.
Steering, lateral acceleration, brake-pressure magnitude and four-wheel energy
are explicitly PROXY. Mass/vehicle/aero/slip/load constants are PRIOR, with
separate ancestry and units recorded in `config.json` and Arrow field metadata.

Past five car samples give a speed derivative. A backward-only position join and
past seven position samples give a local quadratic motion fit. The fitted heading
rate/curvature define steering/lateral proxies, under the documented mathematical
XY convention. This is not a calibrated track model or observed steering.
Support limits and the 50 N wheel-load boundary cause named rejection, never
numerical clipping or gap filling. No measured tyre-energy accuracy follows.

Samples retain native irregular durations. Energy is kJ over the preceding native
interval, and power is kW; `energy=power*dt` is checked on reload. There is no
0.1 s proprietary sampling claim. Forecast experiments must match durations and
horizons and must respect `sequence_id` (one event/driver/stint, split after every
rejected native row). Partition by whole `event_id`; do not feed interleaved
multi-driver rows to the legacy event-only window helper. The separate
[R025 matched forecasting layer](../models/tyre-forecast-benchmark-v1.md) enforces
these boundaries and retains the proxy interpretation.

The public CLI requires five verified archives and the sealed eligible dataset:

```powershell
python -m apexsim.cli build-tyre-energy-dataset --archives PATH_TO_BAHRAIN --archives PATH_TO_AUSTRALIA --archives PATH_TO_MIAMI --archives PATH_TO_MONZA --archives PATH_TO_SINGAPORE --eligible-dataset PATH_TO_R021_DATASET --output .cache/tyre-energy-new
python -m apexsim.cli verify-tyre-energy-dataset .cache/tyre-energy-new
```

`samples.parquet`, `rejections.parquet`, `config.json`, `quality.json` and
`eligible_input.json` are sealed by `manifest.json`, written last. Output must be
a fresh directory outside frozen inputs. Reload works after relocation without
source caches and checks inventory, schema/labels/units, finite targets, source
membership, native-row accounting, bounds and input-mask binding. Hashes establish
local consistency, not provider authenticity. All source manifests retain licence
notes and acquisition/environment metadata. Bulk telemetry stays ignored.

The [frozen protocol](../../research/protocols/TYRE_ENERGY_DATASET.md),
[equations](../../research/equations/TYRE_ENERGY_PROXY_V1.md) and
[verification report](../verification/tyre-energy-dataset-report.md) define
acceptance and limitations. No production or maturity promotion follows R024.
