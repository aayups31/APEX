# R020 permanent benchmark reservation

## A. Current state

2026-10-11, baseline 79861eb, research foundation scoped R1/kernel R0.
R019 is complete: two inspected development weekends, Silverstone/Monza 2024.
Baseline 432 passed, two existing warnings, 151.93 s. The fresh public-data
fixture passes with whole-event partitions and explicit missingness. Existing
untracked artifacts remain untouched and outside the managed data audit scope.

## B. Scope

R020 reserves previously unused whole weekends and enforces their exclusion
from managed development/calibration/model-selection paths. It does not acquire
benchmark telemetry, train a model, score a benchmark or claim R2 accuracy.

## C. Inputs

Master guide 9.1/11.4/12/15-17, replication standard, R019 collection, frozen
2023/2024 Jolpica calendars, existing event/split/pipeline contracts and the
[preregistered protocol](../../research/protocols/PERMANENT_BENCHMARK.md).

## D. Implementation

Select by round modulo four from verified calendar metadata; exclude inspected
events. Audit managed archive identity metadata only. Freeze a complete immutable
reservation, then distribute a sealed digest-pinned policy with the package.
Guard collection membership before native payload reads and experiment splits
before publication/fitting. Revalidate cached pipeline split membership. Preserve
synthetic namespaces and current public-dense-input retirement. Add CLI and tests.

## E. Gate

Real calendar reservation, deterministic membership, no protected native payload
opened/downloaded, no protected event in managed calibration, policy integrity,
alias and cached-path guards, regression/lint and matrix CI. No telemetry data
availability or model-quality requirement is invented for this reservation task.

## F. Risks

Unknown external exposure, ambiguous partial caches, metadata aliases, stale split
or scaler caches, optional guards bypassed by callers, and unavailable providers.
Make project guards default and fail closed. Record limits of the managed audit;
hashes are integrity evidence, not proof of historical human behavior or file ACLs.

## G. Order

Baseline; freeze protocol; metadata inventory and reservation; default policy and
boundary tests; checkpoint push; real offline acceptance; full regression/CI;
machine evidence/backlog closure and final main push. Status IN_PROGRESS.

## H. Implementation checkpoint

Frozen reservation hash
7d690115b7bcd0a52f20acdbf44e628e82efe556b48caf5ebe49b15e29b4ea7d:
nine weekends, eight circuits, two seasons; all sessions protected. Nine managed
archive/snapshot/partial-cache metadata records conservatively identify previously
acquired development weekends. No benchmark native tables are opened or fetched.

The default package policy is sealed and digest-pinned. Collection checks reject
protected query, identity and link metadata before native payload verification;
split checks reject protected numeric or canonical IDs in all ordinary partitions.
Cached stages validate frozen membership before returning scalers. ADR 0005 records
the intentionally tighter public-identity/experiment eligibility boundary.

Final targeted run: 46 passed in 48.49 s. Tests cover selection, metadata-only
access, source mutation, policy tampering/removal/replacement, aliases, unknown
public identity, protected membership in all partitions, cold and cached dataset
stages refusing correctly sealed legacy protected splits before scaler fitting,
and development-corpus refusal before provider verifiers. Repository Ruff passes.
Wheel packaging was checked: policy bytes match the source, and a fresh isolated
Python process loading the extracted wheel layout sees all nine protected weekends.

An independent fresh-process audit denied networking and every native `/tables/`
open while rerunning real metadata selection. It passed with zero network attempts,
zero native table opens and identical membership/exclusions/inspection inventory.
The new timestamp produces a different seal as expected. Audit saved at
`.cache/r020-reservation-check-20261011.json`; repeat reservation at
`.cache/r020-reservation-repeat-20261011.json`. Full regression and CI remain pending
at this implementation checkpoint; R020 stays IN_PROGRESS.
