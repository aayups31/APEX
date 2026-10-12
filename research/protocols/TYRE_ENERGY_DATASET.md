# R024 public tyre-energy proxy dataset: frozen acquisition/feature plan

2026-10-11, baseline 7fefeb4. Scoped research R1/kernel R0. R024 is P0;
R023 robust observations remains a separate P1 study. This is an ADAPTATION
of the existing R006 proxy, not reproduction of proprietary Todd targets.

## A. State and dependencies

R006/R007/R019–R022 are DONE. Existing full regression is 469 passed and latest
Python 3.11/3.12 CI passes. Fresh relevant baseline: five tyre energy/forecast
tests pass (21.14 s); research-demo saves finite 140-row predictions, proxy RMSE
.0554717 kJ and valid terminal resource states. Its existing ridge conditioning
warning is retained. Output `.cache/r024-baseline-research-20261012` is synthetic.
Native race archives and the sealed R021 clean-lap mask supply the public inputs.
Wheel forces, slip, steering, mass and aero load are unavailable as observations.

## B. Scope

Build a versioned, immutable canonical proxy dataset for drivers 4 and 44 in the
five existing 2024 development races (rounds 1/3/6/16/18), chosen before proxy
outcomes are inspected. Include four-wheel energy and power, actual native
interval durations, causal motion/control features, full truth-label ancestry,
native-row lineage, quality/exclusion inventories and portable reload validation.
No training, R025 comparison, track reconstruction promotion or simulator coupling.

## C. Source and units

FastF1 car Speed km/h → m/s; Throttle percent → fraction. Brake is an applied
boolean, not measured pressure: its 0/1 pressure surrogate is explicitly PROXY.
Native X/Y are 1/10 m → metres, documented by installed FastF1 3.8.3 core and
[official source](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/core.py).
Retain native irregular sample times; no claimed 0.1 s proprietary sampling.
Use provider SessionTime only; no cross-provider temporal merge is invented.
Position axes are used as a mathematical XY plane, assuming right-handedness;
physical left/right identification depends on this declared PRIOR convention.

## D. Causal algorithm

Keep car samples within the exact R021 eligible lap intervals. Native table row
identity, driver and compound must match that sealed mask. Use five past car
samples for a linear least-squares speed/time derivative. At each car timestamp,
join only the latest position timestamp <= it (lag <=.35 s). Use seven past
position samples for quadratic XY/time least squares. At the latest position,
`omega=(vx*ay-vy*ax)/(vx²+vy²)`, `kappa=omega/|v_xy|`;
steering proxy `atan(wheelbase*kappa)`, rightward-positive lateral proxy
`a_y=-speed*omega`. These proxies describe local motion, not measured steering,
forces, slip or a calibrated track. All history stays within the same accepted
contiguous stint segment. No centered derivative or future position lookup.

Fixed support priors: native gaps <=.5 s, car history span >=.4/<=2 s,
position history span >=.8/<=2 s; speed [5,105] m/s; geometry/car speed ratio
[.5,1.5]; |longitudinal acceleration|<=30 m/s²; |lateral proxy|<=60 m/s²;
|omega|<=1.5 rad/s; |steering proxy|<=.6 rad. Unknown values, incompatible source
flags, gaps, unsupported motion or wheel normal load <50 N are rejected with
named reasons, not clipped or filled. These are support assumptions, not calibrated
physical limits; no outcome-selected changes are allowed in this frozen version.

Existing R006 energy equation receives mass900 kg, wheelbase3.6 m, track2 m,
CGheight.32 m, front static fraction.46, aero load0 N/front fraction.46,
driven rear fraction1 and brake front fraction.58: all PRIOR. The empirical slip
coefficients and load exponent retain their R006 PRIOR classification. Energy is
kJ over the observed preceding interval; power=kJ/dt in kW. Reconstructing center
motion does not make wheel-specific energy measured. Wheel forces/slips/temperatures
and measured energy remain explicit nullable UNKNOWN fields.

## E. Completion gate

At least 1,000 finite nonnegative target rows per development event; both fixed
drivers represented; complete truth labels for every persisted column; every
native car row either accepted or given an exclusion reason; portable immutable
Parquet reload with exact file/schema/count/hash checks and lineage bounds.
Hand constant-acceleration/quadratic-motion fixtures, independent energy fixture,
future-input invariance, pit/gap boundaries, malformed/protected-input refusal,
relocation and tamper tests. Full applicable regression, lint and matrix CI pass.
Save per-event/driver/compound distributions, native sampling and lag diagnostics,
rejection rates and mass-prior +/-10% sensitivity, without tuning on outputs.
Failure keeps R024 IN_PROGRESS; no fake measured targets or fallback filling.

Implementation clarification after the first public attempt: both fixed drivers
must be represented across the corpus, not necessarily in every event. The code
initially added a stricter per-stream nonempty condition absent from this gate.
Australia/44 has no eligible R021 segment; retain all its native rows as
`no_eligible_stint_segment` exclusions. No driver selection, support prior,
numerical coverage threshold or proxy outcome tuning changed.

## F. Risks

Noisy derivative estimates, position resolution, assumed coordinate handedness,
unmeasured vehicle/slip inputs, retrospective masks, two-driver coverage, dependence
between nearby records and proxy self-consistency do not establish physical truth
or forecast skill. Filter rejection rates and per-event differences stay visible.
No tyre-energy-to-wear causal relationship is established here.

## G. Order

Freeze plan; implement canonical feature/schema/lineage interfaces and tests;
push tested checkpoint; build five-event public artifact; inspect all labels,
distributions/exclusions/sensitivity; full regression and CI; publish data card,
compact evidence, DONE status and closure push. R025/R026 follow separately.
