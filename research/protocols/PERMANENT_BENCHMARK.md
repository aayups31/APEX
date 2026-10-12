# R020 permanent whole-event benchmark reservation v1

Preregistered 2026-10-11 at 79861eb; baseline 432 passed, two existing warnings,
151.93 s. Fresh public-data fixture passes at `.cache/r020-public-baseline-20261011`.
Scope is immutable event reservation and exclusion from ordinary development and
experiment splits. No benchmark telemetry acquisition, inspection or fitting occurs.

Selection rule fixed before implementation: from the already frozen 2023 and 2024
Jolpica calendars, reserve every round divisible by four except events already
inspected for development. Exclude the R019 British/Italian 2024 weekends (12/16).
Use calendar metadata only; no selection by weather, winners, lap times, residuals
or model performance. All sessions of selected weekends are protected. Retain
unavailable future benchmark sources as unavailable; never silently replace members.

Bind the reservation to exact calendar and R019 corpus hashes, a metadata-only
inventory of managed archive identities, creation UTC, rationale, membership and
code hash. The managed `.cache` inventory checks native archive/snapshot identities
without opening telemetry tables. Previously inspected development evidence cannot
be reserved. Untouched means unused for managed APEX calibration, feature tuning,
model selection or outcome inspection; unknown external/user exposure is not proven.
This is a reservation, not a complete acquired benchmark dataset or R2 accuracy.

Publish a sealed permanent project policy as package data with its digest pinned
in the guard. Missing, altered or unsupported policy fails closed. Ordinary event
collections reject protected identities before provider payload verification.
Experiment splits reject them in every partition, including ordinary test sets;
an experiment's test set is not the permanent release benchmark. Check both
canonical event IDs and season/round so renamed events cannot evade the guard.
Real-source unknown/conflicting identities fail; purely synthetic fixtures retain
their separate namespace. Cached pipeline dataset stages must revalidate frozen
membership before returning cached scalers. No override or release evaluation
command is introduced; later benchmark acquisition/evaluation needs its own protocol.

Tests: metadata-only deterministic selection, inspected-event exclusion, no source
payload/network access, seal/schema/digest integrity, immutable output, reordered
membership/aliases, missing policy, guard-before-payload behavior, all experiment
partitions and cached-stage rejection before fitting. Fresh real-calendar artifact
and offline verification, full regression/lint and Python 3.11/3.12 CI must pass.
Freeze membership in Git and preserve prior reservations. Source or coverage
changes require versioned evidence; do not erase old protected events.
