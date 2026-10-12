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
machine evidence/backlog closure and final main push. Status DONE (closed 2026-10-11).

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

## I. Closure and limits

Implementation 0c38ecfdd71367c364905ea820f0e679042a2cf0 is pushed to main.
Full local regression: 450 passed, two existing dependency warnings, 205.85 s,
`.cache/r020-full-20261011`; repository Ruff and whitespace checks pass.
[GitHub CI 38195155493](https://github.com/aayups31/APEX/actions/runs/38195155493)
passed every step on Python 3.11/3.12, including the new permanent-reservation
verification command and all existing data/strategy artifact commands.

Real R019 development collection readback also passes in a fresh socket-audit
guarded process with zero network attempts and unchanged corpus content hash
fe590620134cd63ccfb36b9c0eb79c8e0a0dc8b368582d5ff416e4c889ea922d,
saved at `.cache/r020-development-compatibility-20261011.json`. Existing archive
and canonical evidence remains intact. No benchmark telemetry is acquired or
fitted by this task. Existing public dense training remains blocked.

The [machine evidence](permanent-benchmark-evidence.json) stores the complete
calendar-based reservation, source hashes, managed identity inventory, offline
selection repeat, development compatibility, wheel policy verification and CI
job/step results. Metadata policy is also shipped in the installed package.
Machine-evidence content hash:
0071235774388a0261a9a35e5b29b31b83d518aa831945f508dd138c5f560e21.
R020 is DONE for permanent event reservation and managed calibration exclusion.
This is not an acquired benchmark dataset or a predictive-accuracy result;
unknown external exposure cannot be established by this audit. Later acquisition
and final evaluation need their own frozen protocol. These weekends are not an
ordinary development test set and cannot be silently replaced or unprotected.

Research inventory: 20/73 DONE, 53 remaining; build inventory stays 13/66 DONE.
Research foundation stays scoped R1; production kernel stays R0; R2 accuracy has
not been established. Next: R021 fuel-corrected latent tyre degradation using
separate development lap/stint data, explicit fuel assumptions and rolling-origin
held-out metrics. Preserve the documented Monza OpenF1 stint-coverage limitation;
additional suitable non-benchmark race/stint evidence may be needed for fitting.

Rollback of implementation is a Git revert, preserving the permanent reservation
history and protected membership. Rollback does not authorize benchmark reuse for
calibration. Future schemas/policies require versioned evidence and preserve prior
protected events; no environment-variable or caller opt-out exists.
