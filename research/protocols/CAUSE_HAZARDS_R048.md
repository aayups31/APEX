# R048 published retirement-cause hazards

Use the checksum-pinned F1DB v2026.21.0 CSV result archive. Train on
2022 and 2023, hold out 2024 and 2025, and exclude permanently reserved
events before reading outcomes into the model. The endpoint is
retirement attributed to an incident or mechanical failure in the
published result, not an incident from which a driver continued.

Map explicit collision, accident, crash and spin reports to incident.
Map explicit mechanical or failed-component labels to mechanical.
Keep puncture, damage without an identified cause, illness, withdrawal
and unrecognized reasons unknown. Exclude nonstarters. Count known
finishes through completed laps and a known retirement in the lap
after the last completed lap. Censor unknown retirements after their
last completed lap. Report all unknowns and require at least 90%
classification coverage among retirements in both splits.

Use one Dirichlet half-count per outcome (stay, incident, mechanical).
Compare first-lap and later-lap hazards against constant competing
hazards fit on the same training exposures. The held-out gate requires
at least 20 events of each cause across both evaluation seasons,
improved categorical negative log likelihood, and each cause's
aggregate observed-to-expected ratio within 0.67–1.50. Expected counts
condition on observed driver-lap exposure. Report counts and scores by
season, plus race-level diagnostics. Use no holdout labels to fit.

Acceptance covers published cause labels for retired drivers under the
observed historical regime. Qualification of a simulated full-field
incident process requires separate validation.
