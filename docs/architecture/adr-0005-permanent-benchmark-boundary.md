# ADR 0005 — Separate permanent benchmarks from ordinary experiment splits

Date: 2026-10-11. Status: accepted for R020 infrastructure.

The v1 split contract previously accepted any declared event identities, requiring
only disjoint session/event/known season-round assignments. This is sufficient
for experiment grouping but does not protect a permanent release benchmark from
model selection. In particular, an ordinary `test` partition may be repeatedly
inspected during development. Unknown-round public aliases also cannot establish
whether a reserved weekend has been renamed.

Keep the existing table and split schemas. Add a default project reservation
guard before experiment membership publication/use. All nine reserved weekends
are forbidden in every ordinary partition, including test. Public identities
must resolve by numeric season/round or canonical F1 event ID; conflicting IDs
fail. Synthetic namespaces retain their separate fixture purpose. The broader
table contract still permits unknown observed metadata for archival evidence,
but an unresolved public event cannot enter a modelling split.

The reservation is sealed package data with its digest pinned in source. Missing
or replaced data fails closed; there is no caller opt-out. Development collection
checks run before native payload verification. Cached dataset-stage splits/scalers
do not bypass frozen membership revalidation. Existing public dense ingestion
remains retired. No benchmark acquisition or evaluation command is enabled.

This intentionally tightens the prior experiment-membership behavior without
changing raw/canonical evidence or enabling calibration. The new protocol defines
the scientific separation required by master-guide sections 9.1 and 11.4. Future
release evaluation requires frozen model/feature selections and a separate audited
workflow; missing source coverage must not silently change benchmark membership.

Hashes detect edits; they are not file permissions, signatures, proof of external
human non-exposure or protection against deliberately modified Python code.
Rollback of code must preserve the reservation history and does not authorize
reusing protected events for development.
