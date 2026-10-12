# R019 historical development corpus v1

Preregistered 2026-10-11 at baseline 7fa37e0. R1 research foundation/R0 kernel.
R019 binds multiple historical events to complete verified source archives and
provider-separated canonical observed bundles. R020 benchmark selection is a
separate next slice; this corpus only permits DEVELOPMENT membership. It neither
selects an untouched benchmark nor authorizes public dense-feature training.

Frozen acceptance scope: 2024 British qualifying (round 12, existing inspected
development evidence) and 2024 Italian qualifying (round 16, Monza, a second
development event selected before new telemetry inspection). Existing Jolpica
2024 calendar provides explicit event identities. Official OpenF1 session metadata
resolved Monza qualifying to session 9586, meeting 1244, circuit 39, 2024-08-31.
Its identity-query response is saved separately. Both events are development data
regardless of how useful their later outcomes look. No benchmark member is read.

Freeze one new collection manifest with purpose, membership rationale, event and
session identity, provider-native keys, source-manifest and archive hashes, raw
file counts/bytes, acquisition queries/UTC times/terms references, library versions,
native snapshot schema versions and canonical schema versions/fingerprint. Bind
the observed conversion's source hashes to those exact archives. Preserve schema,
missingness and per-field truth labels; never merge providers or fabricate values.

Require at least two distinct event IDs. Duplicate season/round/session, duplicate
provider session identities, copied aliases, wrong explicit links, unsupported
roles/schemas, unsafe paths, missing/changed files and incomplete runs fail before
manifest creation. Output is exclusive, outside every referenced archive. Paths
are relative to a caller-supplied evidence root and checked to remain within it;
moving that complete root preserves collection identity. Verification uses the
existing offline archive/bundle verifiers and reconstructs each registration.
All source manifests are rechecked before final publication to detect mutation.

Tests include identity/lineage mismatches, duplicates/aliases, malformed membership,
path traversal, output placement/immutability, relocation, tampering and offline
collection integration. The full test suite and Python 3.11/3.12 CI must pass.
Real acceptance must contain both events, both provider archives and the observed
bundles; each newly acquired provider must also pass its offline replay gate.
Inspect inventory/schema/version reports and preserve mapping issues as evidence.
Do not mark R019 DONE with only a simulated or one-event corpus.

Bulk source/cache/canonical files stay ignored. Git receives code, compact
collection/verification snapshots and protocol/report only. Source hashes do not
authenticate arbitrary caches or establish broadcast completeness or causal
feature availability. This is infrastructure, not R2 accuracy or kernel promotion.
References checked for acquisition: [OpenF1](https://openf1.org/docs/) and the
existing frozen [FastF1 archive contract](../../docs/data/fastf1-archives.md).
