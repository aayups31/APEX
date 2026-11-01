# ADR0008: source-labelled conditional imitation after R035

2026-11-01. Accepted for research implementation, subject to its preregistered gates.

The user explicitly requests R036 next. Its direct R035 dependency is complete.
R037/R038 remain later P0 robustness gates; this sequencing choice does not claim
their evidence or advance formal maturity. Production remains unchanged.

The public sources contain no measured steering/body lateral state, so training
a purported human-steering model would manufacture ground truth. R036 instead
uses clearly SIMULATED expert demonstrations in the accepted generic-prior car.
A declared map-preview expert improves the fixed R035 controller; supervised
compact policies imitate its steering correction. Transparent longitudinal and
physical constraints stay shared. Gains from expert design and gains/losses from
distillation must be reported separately.

Event-role guards, training-only normalization, one training-only aggregation
round, frozen selection and complete matched test rollouts follow the
[R036 protocol](../../research/protocols/IMITATION_DRIVER.md). The task closes only
if the learned component actually beats frozen R035 without instability. No
claim of improved real-car pace, human style, formal R4 or production promotion
follows. Rollback is removal/reversion of isolated R036 research modules and
commands; accepted R035 and production dynamics are not changed.
