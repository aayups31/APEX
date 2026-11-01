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
and event/sequence uncertainty. R029's
[accepted reference-geometry study](../verification/track-reconstruction-v3-report.md)
passes all 48 test laps across Bahrain/Monza, with preserved prior failures,
source-only target support, ten-lap sensitivity, native audit and portable replay.
Research inventory is 36/73 DONE; build inventory 13/66. The scope is registered
reference shape, with unknown surveyed road properties and no production promotion.
R027/R028's [accepted explanation study](../verification/forecast-explanation-report.md)
adds independent temporal faithfulness tests and finite-catalogue counterfactual
validity on all ten frozen checkpoints. Unsupported/unstable cases abstain;
feasibility is conditional on declared kinematic/proxy and marginal-support
checks. Full real-car intervention feasibility remains UNKNOWN.
R030's [accepted longitudinal calibration](../verification/longitudinal-calibration-report.md)
reduces held-out high-speed/full-throttle section error42.1% versus its strongest
baseline. Effective ratios, unsupported DRS identification and parameter-only
uncertainty limitations are explicit. R031's
[bicycle force/stability study](../verification/bicycle-dynamics-report.md)
is complete on synthetic priors: 13 supported paths and one preserved yaw-limit
abstention challenge, with 634 passing tests and independent numerical replay.
R032's [aero/load-transfer study](../verification/aero-load-transfer-report.md)
passes its synthetic sensitivity/identifiability gate. R033's
[recorded observation alignment](../verification/recorded-replay-alignment-report.md)
passes frozen public coverage on88 laps/30,299 rows, with all150 longitudinal
inputs supported. Complete measured bicycle readiness remains0%; unknown states
are not fabricated. R034's [matched-horizon report](../verification/open-loop-errors-report.md)
is complete:505 supported cases,95 explicit abstentions,2525 independently checked
paths. Continuous full physical lap/stint replay remains unavailable. R035's
[conditional research driver](../verification/transparent-driver-report.md) completes
all four frozen held-out nominal lap conditions, with maximum reference error<.33m,
independent full-lap replay and timestep refinement. All690 tests pass locally and
on Python3.11/3.12 CI. Its generic-prior simulated laps remain about48s slower than
the source laps; real-car pace calibration and full measured replay are unresolved.
R036's [conditional imitation driver](../verification/imitation-driver-report.md)
is complete: a simulated-expert-trained policy reduces nominal tracking RMSE23.6%
versus R035, with all eight final cases passing and44 exactly regenerated runs.
Worst nominal peak error increases from.326m to.383m; the analytic expert remains
equally accurate. All713 tests pass locally and on Python3.11/3.12 CI.
Next priorities are R037 multi-lap drift/recovery and R038 OOD/fallback.
These scoped component completions do not promote formal maturity.
Benchmark reservation alone is not acquired benchmark telemetry;
the production kernel remains R0 and a separate R2 review is still required.

## Kit manifest

The kit manifest records the files and components included in the project package.

It is intended for traceability and verification rather than runtime use.
EOF
