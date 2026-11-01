# Conditional continuous driver recovery and runtime supervision

Research components under evaluation; foundation R1, production R0 unchanged.
[ADR](../architecture/adr-0009-recovery-and-fallback.md),
[data contract](../data/closed-loop-recovery-support.md),
[equations](../../research/equations/RECOVERY_SUPPORT_V1.md).

R037 tests frozen R035/R036 controllers over five continuous laps on four supplied
Monza source conditions, including repeated signed steering disturbances. It
measures compounding error and sustained return to a matched nominal trajectory.
R038 adds an eight-feature empirical support envelope and a three-mode supervisor:
learned steering, transparent R035 fallback, or latched abstention. Invalid learner
features/actions can trigger fallback only while independent trusted pose/map and
vehicle assumptions remain valid. Ten supported low-score commands precede release.

The fallback is the existing transparent controller, not a second learned model.
It uses the same pace/vehicle and preserves actual steering memory. No fake state
reset, path constraint, hidden speed reduction or production promotion is introduced.
The policy weights remain the frozen R036 checkpoint. The detector stores eight
centers, eight half-ranges and a cutoff with explicit prior floors/hysteresis.

```powershell
apexsim prepare-recovery-benchmark --reference .cache/r036-evaluation-20261101 --output .cache/r037-inputs-NEW
apexsim run-recovery-benchmark --inputs .cache/r037-inputs-NEW --output .cache/r037-run-NEW
apexsim verify-recovery-benchmark .cache/r037-run-NEW --receipt .cache/r037-replay-NEW.json
apexsim fit-support-detector --recovery .cache/r037-run-NEW --verification .cache/r037-replay-NEW.json --output .cache/r038-detector-NEW
apexsim verify-support-detector .cache/r038-detector-NEW
# Push frozen detector parameters and source catalog before held-out fault runs.
apexsim run-support-benchmark --detector .cache/r038-detector-NEW --output .cache/r038-run-NEW
apexsim verify-support-benchmark .cache/r038-run-NEW --receipt .cache/r038-replay-NEW.json
```

All destinations must be new. Offline source packages are required locally;
published metrics/hashes do not redistribute provider binaries. Full scientific
replay requires the exact frozen implementation snapshot. Rollback is removal of
isolated new research modules/commands, leaving accepted dynamics and production
unchanged.

Limitations: generic vehicle, supplied map/perfect simulated localization, no
thermal/fuel/energy evolution, finite intervention catalog and reused event data.
Source pace mismatch persists. An axis-aligned support envelope misses correlated
or in-envelope changes and unobserved physics. Finite fallback tests provide no
invariant-set proof or real-world safety certification. Fault injections are
constructed tests, not an estimate of real fault prevalence.
