# R026 cross-season proxy evaluation data card

The four 2023 race archives are BahrainR1, AustraliaR3, MonzaR14 and SingaporeR15
under verified completed-event Jolpica/FastF1 numbering. Their date/name/round
identities agree before telemetry acquisition. All are non-benchmark development
events, with exact offline reconstruction and zero network attempts. The nine
permanent whole-event benchmark reservations remain excluded.

Drivers4/44 are fixed, without replacements based on coverage or outcome. R021's
retrospective clean-dry eligibility, exact green/accurate/non-deleted flags,
pit exclusions and contiguous six-lap minimum segments remain unchanged. Every
selected-driver native car row becomes an accepted proxy sample or receives an
exclusion reason, including absent eligible stints. No interpolation, filling or
relaxed geometry/load thresholds are introduced for the new season.

The same R024 schema, source labels, units, motion reconstruction, vehicle/slip
priors and four-wheel energy equations are used. The configuration file must
match R024 byte for byte. Energy is a PROXY in kJ over the preceding native
interval; measured wheel force/slip/energy stays null UNKNOWN. Public provider
values may include upstream reconstructions. Fixed priors are not calibrated
2023 car specifications or measured tyre parameters.

The new dataset has its own sealed samples, exclusions, quality/config, eligible
input and manifest. Original R024/R025 inputs stay immutable. See the
[R024 source/physics card](tyre-energy-proxy.md) for the mathematical assumptions
and the [R026 report](../verification/track-generalization-report.md) for actual
coverage, sequence/window counts and source seals.

Circuit stratum derives from the R025 training vocabulary, never from evaluation
performance. Eight-sample windows cannot cross event/driver/compound/segment or
native-row boundaries. The R025 scaler/vocabulary is loaded rather than fitted
on these events. Both evaluation strata are 2023; temporal/vehicle/driver/layout
shift remains separate from any causal claim about unseen circuits.

Bulk telemetry, caches, predictions and model files stay in ignored local
storage. Git retains compact manifests/results and verification evidence. Source
rights remain with the providers; no confidential team data is included.
