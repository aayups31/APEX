# Permanent whole-event benchmark reservation v1

R020 reserves nine weekends before benchmark telemetry acquisition or modelling.
The authoritative project policy is packaged as `apexsim/data/benchmark_policy.json`
with schema `apex-permanent-benchmark-reservation-v1`. Its sealed digest is pinned
in `benchmark_guard.py`; installed wheels include the policy. Missing or altered
policy data fails closed. There is no opt-out argument.

Selection uses frozen 2023/2024 Jolpica calendar metadata: every round divisible
by four, excluding acquired/inspected development weekends. Silverstone and Monza
2024 are excluded. No winner, weather, lap time or model score informs selection.
Every session of these weekends is protected:

| Season | Round | Circuit |
|---|---:|---|
| 2023 | 4 | Baku |
| 2023 | 8 | Montreal |
| 2023 | 12 | Spa |
| 2023 | 16 | Suzuka |
| 2023 | 20 | Interlagos |
| 2024 | 4 | Suzuka |
| 2024 | 8 | Monaco |
| 2024 | 20 | Mexico City |
| 2024 | 24 | Yas Marina |

The policy binds exact calendar snapshots/archive hashes, development-corpus hash
and a metadata-only managed archive inventory. It contains no on-track telemetry,
predictions, performance scores or acquired benchmark dataset. Unknown external
human exposure is outside the managed audit claim. Unavailable future source
coverage is recorded, not replaced with another weekend.

Development corpus checks reject protected FastF1 query/identity and link metadata
before native payload verifiers run. Split creation/readback reject benchmark events
in train, validation AND ordinary test partitions. Renamed event IDs cannot bypass
numeric season/round identity; conflicting or unresolved public identities fail.
Synthetic fixtures keep their separate namespace. Cached pipeline scalers do not
bypass revalidation of frozen membership before return/use.

```powershell
.venv/Scripts/python.exe -m apexsim.cli verify-benchmark-reservation apex_engine/src/apexsim/data/benchmark_policy.json
```

Generation requires fresh output and the original calendars/development collection.
It does not replace the active project policy:

```powershell
.venv/Scripts/python.exe -m apexsim.cli freeze-benchmark-reservation --calendars .cache/jolpica-2023-20260916 --calendars .cache/jolpica-2024-20260916 --development-corpus .cache/development-event-corpus-20261011.json --evidence-root .cache --output .cache/reservation-new.json "Permanent whole-event benchmark reservation"
```

No release benchmark acquisition/evaluation workflow is enabled here. Later access
requires its own protocol after model/feature choices are frozen. A hash is an
integrity check, not access control or proof a person never saw a race. See
[ADR 0005](../architecture/adr-0005-permanent-benchmark-boundary.md) for the explicit
tightening of ordinary experiment split eligibility.
