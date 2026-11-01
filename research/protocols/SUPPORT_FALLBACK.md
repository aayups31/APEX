# R038 conditional support detector and transparent fallback

Preregistered2026-11-01 before detector fitting or held-out fault evaluation.

## A. Current state

Same baseline/maturity as [R037](MULTILAP_RECOVERY.md). R038 execution requires
an accepted and independently replayed R037 package. R037 is not presumed passed.

## B. Scope

Fit an empirical observation-support envelope using R036 training features only,
calibrate its cutoff on frozen R036 validation episodes only, and supervise frozen
learned steering with R035 transparent feedback. Test detection, fallback,
hysteresis, explicit abstention and finite failure cases. No production promotion,
new vehicle physics, statistical uncertainty guarantee or universal safety claim.

## C. Sources and adaptation

Slagel et al.,2024, *A Verification Framework for Runtime Assurance of Autonomous
UAS*, [NASA primary paper](https://ntrs.nasa.gov/api/citations/20240007986/downloads/DASC_submit_slagel_v01.pdf),
read2026-11-01. Adapt only the advanced-controller/monitor/reversionary-controller
decomposition. This implementation has finite empirical tests, no PVS/DDL proof,
barrier certificate, invariant safe set or aircraft-result replication. Detection
can miss shifts inside its envelope; a trusted fallback requires trusted pose/map.
The source paper's formal guarantee is not claimed for APEX.

## D. Frozen algorithm and inputs

Eight causal R036 features retain their units/truth labels. Training base features
only: q.005/q.995 per coordinate, center midpoint, half-range with declared floor
[.05,.02,.02,.005,.005,.02,.01,.01]. Score=max_i abs((x_i-center_i)/half_range_i).
Validation cutoff=max(1.25,1.1*validation-score q.995). This is an empirical box,
not a conformal probability or coverage bound. Store source/row ledgers and all
parameters. Freeze/push before any R038 test outcomes. No test calibration.

Monitor100ms. Hard missing/untrusted state/map or changed known vehicle assumptions
=>latched ABSTAIN before integration. Finite state must remain in R031 support
and within2m reference error. Feature score>cutoff or nonfinite/out-of-bound
raw learned correction(abs>.2rad)=>FALLBACK immediately; nonfinite feature data
also fallback if independent trusted pose/map remain valid. R035 fallback computes
its own features/actions from trusted current state/map, never corrupted learner
features. Release after10 consecutive supported commands below.8cutoff with valid
candidate correction. Steering memory/rate and common force constraints are shared;
switches do not teleport or reset state. ABSTAIN terminates the simulated prefix,
not a claimed physical emergency stop. Known parameter/map assertions cannot
detect an unobserved physical grip change.

## E. Evaluation and gates

Four unchanged source conditions, three continuous laps. Nominal compares unguarded
learned, guarded learned and always-transparent (12 runs). At1.25L and2.60L inject
20-command learner-only faults: preview feature shift(+10*half_range*cutoff),
raw residual bias(+.3rad), nonfinite learner residual. Compare guarded/unguarded
for all faults(24 runs); four guarded residual-bias refinements. Same trusted map,
state, pace and actuator limits. Unsafe baselines retain stopped prefixes. Twelve
hard-boundary cases(4conditions*missing map/untrusted state/known parameter mismatch)
must abstain at t=0 with no action or integration. Add offline feature-axis boundary
and subthreshold blind-spot probes; report conditional sensitivity/false alarms,
not real-world OOD accuracy.

Required40 physical runs include unsafe baselines without requiring those baselines
to complete. All16 guarded runs and four transparent nominal runs must complete
three laps with max reference error<=2m/P95<=1m and unchanged R037 physical limits.
Every injected fault must trigger fallback on its first command, no faulted learned
action reaches dynamics, and guarded fault cases return to learned control after
the final fault. No chatter: release requires10 good commands. Nominal guarded
fallback fraction<=5% per condition, nominal completion<=1.01*unguarded, nominal
RMSE<=max(1.1*unguarded,.15m). Report all triggers, false alarms, switches, fallback
time and action projections; detector calibration/margins are fixed beforehand.
All hard-boundary cases abstain. Same timestep/independent tolerances as R037;
independent full guarded residual-bias run plus seam/switch representative checks.
Exact inventory/catalog guards and complete scientific regeneration of all paths,
detector fit/validation, metrics and decisions required before DONE. Smoke cannot
close public R038. Full regression/CI, report/cards/equation map and retained failures
are mandatory. If a gate fails, preserve failure; no silent test retuning.

## F. Risks

An axis-aligned envelope misses correlated/in-envelope shifts, unknown physics and
unmodelled threats. Injected faults are constructed, not measured faults. Perfect
independent simulated localization is a strong assumption. Transparent fallback
is empirically supported only in this conditional operating envelope; there is no
invariant-set safety proof or real-world safety certification.

## G. Order

Finish R037; fit/check detector on train/validation; commit/push frozen detector;
evaluate every held-out case, failure baseline and hard boundary; independently
audit/refine and regenerate all paths; publish; run full regression/CI; close only
on every gate. R039 thermal physics follows, without bypassing maturity review.
