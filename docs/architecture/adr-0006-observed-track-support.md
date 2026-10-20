# ADR0006: separate R029 observed-support reconstruction experiment

Date:2026-10-19. Status:accepted for research implementation under the user's
request to complete R029. No production-component promotion.

R029 v1 rejected14/24 selected laps for interior native position gaps. Its full-lap
source assumption failed; its geometry estimator was never fitted to public data.
The v1 protocol, evidence, report and failed decision remain immutable records.

Use a separate [v2 protocol](../../research/protocols/TRACK_RECONSTRUCTION_V2.md):
retain native vertices and explicitly unsupported intervals, combine ten training
laps, demand at least three independently supported laps at every10m station,
exclude unsupported curvature stencils and quantify leave-one-lap sensitivity.
The.75s native interval and boundary-bracket limits are unchanged. V2 changes the
scientific question from every lap being complete to the union of observed
training traces supporting a complete reference shape. It is not a retroactive
v1 pass or a silent gap-limit increase. New geometry holdout laps are frozen
before shape fitting; prior development reuse remains disclosed.

The alternative of simply increasing.75s, replacing failed v1 laps or claiming
that periodic model closure validates missing source observations is rejected.
The v2 gates retain the original XY/curvature tolerances and add coverage,
maximum error, support fraction and sensitivity requirements.

R029 can close only with a passing separate v2 public study plus complete replay,
regression and CI evidence. Research R1/kernel R0 maturity remains unchanged.
Road width, surveyed centerline, validated elevation, official zones and full
pit route remain UNKNOWN; accepted reference shape is not a production road model.
