# Project Management

This directory contains project-planning and package-tracking material.

## Files

- [Build backlog](build-backlog.csv)
- [Kit manifest](kit-manifest.json)
- [Current scoped maturity status](maturity-status.json)
- [Engineering target and evidence expected by a motorsport reviewer](engineering-target.md)
- [R1 evidence-gate review](../verification/r1-gate-review.md)
- [Local platform and API](../platform/README.md)

## Build backlog

The build backlog tracks implementation tasks, dependencies, priorities, and maturity stages.

Work should be selected according to the dependency order defined in the [Master Build Guide](../../00_MASTER_BUILD_GUIDE.md).

The research foundation has passed R1 within the reviewed FIENI equation-level
adaptation scope. The production simulation kernel remains R0. These are
different evidence domains: the review does not deploy research policies or
establish R2 public-data accuracy. R019's two-event development corpus is complete;
R020's separate nine-weekend permanent benchmark reservation is complete.
R021/R022's five-race public tyre-pace study is complete with fixed fuel priors,
rolling evaluation and Bayesian hierarchical prediction. Its validation interval
adjustment undercovers nominal 90% on held-out tracks; the frozen descriptive gate
passes, without a maturity promotion. R024's source-bound tyre-energy proxy
dataset is complete, including labelled assumptions and native exclusion accounting.
R023's conditional robust observation comparison and R025's genuine six-family
forecast benchmark are documented in the
[latest verification report](../verification/robust-tyre-forecast-report.md).
R026's [frozen seen/unseen evaluation](../verification/track-generalization-report.md)
is complete on four separate 2023 development races, with preserved model weights
and event/sequence uncertainty. The next dependency-priority P0 task is R029
track reconstruction. R027/R028 remain pending P1 explanation/counterfactual work.
Benchmark reservation alone is not acquired benchmark telemetry;
the production kernel remains R0 and a separate R2 review is still required.

## Kit manifest

The kit manifest records the files and components included in the project package.

It is intended for traceability and verification rather than runtime use.
EOF
