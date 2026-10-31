# R034 matched open-loop error and support report

Frozen2026-10-31 before new replay error evaluation. ADAPTATION; research only.

## A. Current state

Base d31a7fe0b787745e9ef6276b4b66b30891ba0acd; fresh664 tests pass in581.90s,
two existing dependency warnings, Python3.12.12/Windows. Fresh recorded-replay
reference `.cache/r034-baseline-reference-20261031` verifies with zero difference,
seal `a1f0279d947257192ec97ac9c919c00e1b4e7db445d6bab2417b8b1cb6ea2842`.
R030/R033 are accepted. Foundation R1/kernel R0 remain; formal R3 is not achieved.

## B. Scope

Complete R034's report of matched section/lap/stint horizons, regimes and
abstentions. Do not silently extrapolate the R030 high-speed/full-throttle model
into braking, corners or complete laps. No refitting, new model selection,
synthetic steering observation, benchmark access or production promotion.
Reporting an unavailable horizon explicitly is required; it is not a successful
full-car replay. R035 is a separate conditional research controller experiment.

## C. Source truth and dependencies

Frozen R033 package seal
`42cede289de897d6153ae3f66d84631de5394911fa979d5df453316b92912620`, all88 source
laps and150 R030 sections. Frozen R030 development seal
`82fc70acfef2a5c730ba908d6659ff35a1730aac1d5663612029c03333081e99`;
model payload `598d646b23e1eeb8ea0d6a88a5f2f4d54656ef7af91e4de01597abc2460c713b`.
The selected shared-drag model and all four baselines stay frozen. Splits remain
2023 Bahrain/Monza train,2024 Bahrain validation,2024 Monza test. These are reused
development events; nine reserved benchmark events remain protected.

Source-only clock preflight: only7/88 laps have maximum native car gap<=.5s,
48/88<=1s; maximum1.32s. Do not bridge these gaps to fabricate continuous full
physics replay. The public sources have no complete measured chassis controls
or initial state. Native stint membership is available from source lap tables;
missing intervening laps must prevent a continuous-stint claim.

## D. Method and outputs

Evaluate all150 immutable sections at exact horizons {.5,1,2,3}s, retaining a
reason when the original section is too short. Use the union of native timestamps
and the requested endpoint; source throttle/DRS is held left-constant, initial
speed and five-sample causal slope are the only observed state initialization.
Endpoint observed speed interpolation is labelled RECONSTRUCTED_TARGET, never
fed to a rollout. Match nodes/horizons/inputs across shared_drag, physical_prior,
legacy_huber, constant_speed and constant_acceleration.

Report future-node MSE/RMSE, MAE, endpoint and speed-integral distance errors;
initial node excluded. Average sections within lap, laps within driver, drivers
within event, events within split equally. Report origin speed bands40–60/60–80/
80–105m/s, DRS state and track. This supported mode is high-speed/full-throttle/
low-reference-curvature; all other physical regimes explicitly abstain.

Lap and native-stint summaries aggregate supported section errors and coverage
and are labelled SECTION_AGGREGATE_NOT_CONTINUOUS_REPLAY. Full-lap/full-stint
physics errors are null with explicit missing-control/state/calibration reasons.
Additionally report full sampled-lap constant-speed diagnostics, using the same
first observed state and all source speed targets, clearly separate from supported
physical section scores. Do not report those diagnostics as validated dynamics.

Add immutable CLI report/verify/audit, source/protocol snapshots, frozen input/model
bindings, exact inventory and portable arrays. Reuse accepted modules without
changing their scientific behavior. Independent scalar equations and DOP853 check
the horizon paths and reconstruct scores separately.

## E. Acceptance and stopping gate

All150 sections/all88 laps accounted for; supported+abstained horizon cases equal
the full Cartesian source catalog. Every method uses identical supported nodes.
Both test drivers must have results at each horizon; unavailable cases retained.
All lap/stint aggregates are explicitly noncontinuous; no complete measured
chassis readiness is promoted. Every raw baseline physical-domain violation is
reported, with no speed clipping. Frozen model/choice is verified, never retuned.
Independent path agreement<=1e-6m/s; independently recomputed scores atol1e-7,
rtol1e-6. Scientific replay rtol1e-7/atol1e-8, exact stored hashes separate.
Hand metrics, causal target perturbation, short-horizon, grouping, missing-stint,
source/benchmark guards, portability, tampering and false-completion tests pass.
Full applicable regression/CI, inspected report/evidence/model card required.
DONE closes the reporting gate, not unavailable full-car validation.

## F. Risks

Reused events and frozen-model selection history; interpolated evaluation endpoint;
source timing and source geometry conditions; limited supported domain; section
aggregation can conceal missing lap/stint support unless explicitly separated.
Uncertainty bands remain uncalibrated. Report all limitations beside the metrics.

## G. Order

Commit protocol; implement/test matched horizons and support accounting; push;
immutable source-bound study and independent audit; push; evaluate/publish all
scopes and exclusions; full regression; close reporting gate only.
