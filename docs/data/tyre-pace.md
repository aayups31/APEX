# Public race-lap dataset card: R021/R022

The dedicated tyre dataset uses verified full FastF1 race archives for 2024
Bahrain, Australia, Miami, Monza and Singapore. It is separate from R019's
dual-provider qualifying corpus. The permanent nine-weekend benchmark remains
excluded before payload access. No benchmark telemetry was acquired.

The dataset contains 267 contiguous segments and 4,538 eligible laps from 5,423
native rows. Each retained lap carries its native row position, driver, race lap,
stint, compound, tyre age, observed seconds, prior fuel effect and corrected
seconds. Every excluded row has reasons; reason totals can overlap. Segments
under six laps are excluded. Numeric pace outliers are retained.

Required native flags are explicit accurate/non-deleted, exact green status `1`,
dry S/M/H and no pit timestamps. Unknown fields fail eligibility. Gaps and
stint/compound changes reset the latent state. This is a retrospective clean-lap
evaluation target, not a live flag or future lap-quality predictor.

| Field | Truth boundary |
| --- | --- |
| Lap time, flags, stint, compound, tyre age | FastF1 parsed source; upstream reconstruction possible |
| Initial fuel, burn, seconds per kg | PRIOR: 105 kg, 1.4 kg/lap, .030 s/kg |
| Fuel-corrected pace | PROXY, not measured fuel or measured physical wear |
| Latent state/drift | MODEL_ESTIMATE, with driver/traffic/weather confounding |

Each archive has exact offline replay with no network attempts. The input seal,
calendar/archive/table hashes, source versions, rejection inventory and environment
bind the study. Bulk provider data and weights remain in ignored `.cache`; Git
holds aggregate evidence and manifests. Hashes establish local integrity, not
provider authentication or independent physical truth.

From the repository root, with APEX installed:

```powershell
python -m apexsim.cli build-tyre-dataset --archives PATH_TO_BAHRAIN --archives PATH_TO_AUSTRALIA --archives PATH_TO_MIAMI --archives PATH_TO_MONZA --archives PATH_TO_SINGAPORE --calendar PATH_TO_VERIFIED_2024_CALENDAR --output .cache/tyre-input.json
python -m apexsim.cli tyre-degradation-demo .cache/tyre-input.json --output .cache/tyre-study
python -m apexsim.cli verify-tyre-study .cache/tyre-study
python -m apexsim.cli tyre-degradation-smoke --output .cache/tyre-smoke
```

All outputs require fresh paths. The default research run fits the frozen public
study and fuel sensitivities. The last command is SIMULATED offline execution
verification only and cannot close either public-data task. Artifact reload
verifies all file seals, input/summary binding and finite posterior array shapes
without refitting. See the [model card](../models/tyre-pace-v1.md),
[protocol](../../research/protocols/TYRE_DEGRADATION.md) and
[verification report](../verification/tyre-degradation-report.md).
