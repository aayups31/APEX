# ADR0009: continuous recovery and empirical runtime supervision

2026-11-01. Accepted research design, conditional on frozen acceptance gates.

R037/R038 extend accepted R035/R036 in isolated research modules. The new runner
must preserve their first-lap behaviour and continuous R032 chassis state across
seams. Disturbances act on commands; no pose or state resets conceal drift.
R038 uses independent trusted state/map for its transparent fallback and terminates
explicitly when those assumptions fail. It cannot certify safety or identify an
unobserved real-world change using generic priors alone.

The [R037](../../research/protocols/MULTILAP_RECOVERY.md) and
[R038](../../research/protocols/SUPPORT_FALLBACK.md) protocols fix catalogs,
thresholds, source splits, negative controls and closure conditions. Freeze and
push detector parameters before test. Keep accepted source files and production
unchanged. Rollback removes the isolated new research modules/commands; it does
not invalidate or rewrite frozen R035/R036 artifacts. Formal maturity remains
R1 research foundation/R0 production kernel pending separate review.
