# R033 native replay observation and input map

Public parsed-source **ADAPTATION**. The
[protocol](../protocols/RECORDED_REPLAY_ALIGNMENT.md) freezes the entire cohort,
field semantics and coverage thresholds before public alignment is evaluated.

| Quantity | Conversion / meaning | Truth |
|---|---|---|
| t |native SessionTime seconds; Date increment check|parsed source, physical latency unknown|
| speed |native Speed /3.6, m/s|parsed source; body vx unknown|
| throttle |native Throttle /100, fraction|parsed source|
| brake_on |native Brake, strictly boolean|parsed on/off; force/pressure unknown|
| rpm / gear |native RPM / nGear|parsed engine speed/gear; torque/ERS unknown|
| drs_open |{0,1,8}->0; {10,12,14}->1; others nullable|documented mapping; surveyed zone unknown|
| x,y |latest same-lap native X,Y *.1, m|parsed source coordinate; no interpolation|
| position age |t_car-t_position, s|reconstructed|
| reference curvature |frozen R029 registered trace, 1/m|offline reference conditioning|
| steering, body vx/vy, yaw, fuel, battery |nullable fields with no default value|UNKNOWN|

Each frozen lap uses half-open [start,end) membership. Native car/position IDs
retain original table order. Both clocks must be finite/strictly increasing;
their Date increments must agree to1e-6s. No offset is fitted and no inaccurate
telemetry `Time` field is substituted.

At a native car row i, select the largest same-lap position index j with
`t_pos[j]<=t_car[i]`. Require at least one prior native position in the same lap,
age<=.35s, previous gap<=.75s, native Source=pos, OnTrack and finite XY. Missing
or stale associations stay nullable and retain their rejection reasons.

Joint observed readiness is the conjunction of valid native speed, throttle/
boolean-brake/known-DRS, RPM/gear and a supported causal position. It does not
include inferred chassis or hidden power-unit state. Full measured bicycle
readiness is separately reported as unavailable when those required fields are
unknown. Reference curvature is never converted silently into measured steering,
body lateral velocity or yaw rate.

Row coverage divides ready rows by **all** source car rows in all88 frozen laps.
Interval coverage sums adjacent native intervals <=.5s with ready left endpoint
and valid next speed, divided by complete lap durations, including missing
prefix/tail. It is supported-observation interval coverage, not a claim that a
stale position is a continuous measured trajectory between samples.

R030 section inputs retain exact source rows, sample times, held throttle/DRS and
observed initial speed. Future observed speeds remain evaluation targets. The
input type has no future speed-target field and never teacher-forces a prediction.
Boolean braking is not converted into physical force. No complete measured
bicycle adapter is constructed without the missing required fields.

Independent audit uses a scalar backward pointer, direct native conversions and
independent interval accounting. Source hashes, causal field checks, frame
regeneration and gate replay are separate evidence checks. Neither timing
alignment nor exact scientific replay establishes vehicle prediction accuracy;
that is R034 and later work.
