# R037/R038 continuous recovery and support evidence contract

Status: implementation/evaluation; closure is governed by the frozen
[recovery](../../research/protocols/MULTILAP_RECOVERY.md) and
[support](../../research/protocols/SUPPORT_FALLBACK.md) protocols.

The source is accepted R036, including its event-guarded R035/R033/R029 lineage.
No new telemetry is acquired. All nine protected benchmark events remain untouched.
2023 Bahrain/Monza feature episodes fit the detector;2024 Bahrain episodes set its
cutoff; four unchanged2024 Monza initial conditions evaluate continuous driving.
These are reused development events, not independent unseen-circuit proof.

| Quantity | Truth and scope |
|---|---|
| Supplied XY/tangent/curvature | RECONSTRUCTED registered reference, not surveyed road |
| Initial scalar speed | PARSED_SOURCE, not complete measured chassis state |
| Initial vy/yaw rate | zero PRIOR |
| Subsequent six-state trajectory/actions | SIMULATED |
| Vehicle/grip/aero/power | GENERIC_PRIOR |
| Steering pulses/learner faults | declared SIMULATED interventions |
| Support center/ranges | fitted training-feature descriptive model |
| Support cutoff | validation-calibrated empirical threshold, not probability |
| Trusted state/map and known parameter assertion | simulated experiment assumption |
| Real steering/true body state/road boundary | UNKNOWN |

R037 freezes exact source/code inventories before evaluation. Each research run
contains five continuous laps; smoke three. Station is unwrapped, body state and
steering memory never reset at seams.100ms controls and RK4 substeps<=.02s retain
the accepted physical limits. Signed command pulses occur twice; large challenges
retain prefixes and failures. NPZ contains time, six states, station, lateral
error, actual applied controls and the causal trusted-state feature vector.
JSON stores event windows, complete per-step decisions, metrics and rejected state.

R038 freezes detector parameters before test. Training-only robust feature ranges
and validation-only cutoff retain source row counts/ledgers and independent scalar
fit checks. Faulted learner features are reconstructed from the frozen injection
recipe; stored features remain the trusted causal features. Every decision records
support score (null if unavailable), mode/reason, active fault/first fault command,
and candidate validity. A missing score is never interpreted as supported.
`learner_action_evaluated` distinguishes an unavailable/skipped inference from an
evaluated invalid candidate. Invalid or outside-envelope features are checked
before guarded inference, and transparent feedback does not require the learner.
Nonfinite candidate actions are detected before actuation; numeric NPZ trajectories
remain finite. Hard-boundary abstention has zero controls and one initial state.
It terminates a simulation; it is not a physical emergency-braking implementation.

Every output directory must be fresh. Portable nested sources, manifest hashes,
source snapshots and truth bindings precede mathematical regeneration. Full
regeneration checks trajectories, catalogs and metrics separately from independent
scalar-load/DOP853 numerical audits. A smoke package is never public-task eligible.
R038 additionally checks independent physics immediately before and after every
recorded handover in its main.02s guarded runs; full-path numerical replay and
these switch checks have separate bound receipts.
An empirical envelope cannot certify safety or identify all distribution shifts.
