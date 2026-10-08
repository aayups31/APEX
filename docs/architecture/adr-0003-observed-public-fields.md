# ADR 0003: Replace fabricated public CSV features with nullable evidence

- Status: accepted
- Date: 2026-10-08 (draft initiated 2026-09-19)
- Scope: P1-07; extends ADR 0002

## Context and decision

The legacy public CSV adapters supply constant weather, compound, pit, grip and
race-control values, interpolate independently sampled streams and fabricate some
missing controls. Their dense contract cannot preserve per-value unknowns. P1-06
also demonstrated incompatible lap-start semantics and overlapping OpenF1 stint
boundaries. Continuing to label these dense outputs as public observations violates
the master guide's truth-label and missingness requirements.

Replace these converters with `build-observed-tables`, which reads verified native
archives plus an explicit checked session link and emits separate provider bundles
under the existing public-tables-v1 contract. Preserve source values, units, nulls,
row lineage and unknowns. Never cross-fill providers or infer pit occupancy from
missing messages. Quarantine stint rows that overlap under the canonical inclusive
range contract; ambiguous lap-to-stint matches stay unknown. Raw records remain in
the immutable archives and quarantine references remain in the conversion report.

The former `ingest-fastf1` and `ingest-openf1` functions/commands remain recognizable
but fail before network or filesystem mutation with migration instructions. Existing
public dense CSV inputs are rejected by the training ingestion boundary, including
when they have valid old source manifests. The synthetic CSV pipeline is preserved.
An explicitly evaluated, missingness-aware feature builder is required before
public evidence can become dense model input; this milestone does not provide one.

## Consequences and rollback

This intentionally changes the public-ingestion API's behavior. Users move to
`download-*`, `align-public-data`, and `build-observed-tables`, then inspect or
validate the resulting Parquet evidence. No schema version is silently redefined,
no simulation kernel is changed and no model is promoted. Null pit timestamps mean
unknown, not a claim that the driver was outside the pits. Current outputs are
retrospective evidence; they do not establish online availability of observations.

Reverting this commit restores the previous API, including its known unsafe
assumptions; historical artifacts are not rewritten. Frozen native archives and
prior acceptance evidence remain intact.
