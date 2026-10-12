# Robust tyre observations v1 model card

Task R023, ADAPTATION, conditional research use. The frozen decision, metrics,
artifact seals and verification are in the
[R023/R025 report](../verification/robust-tyre-forecast-report.md).
The [equation map](../../research/equations/ROBUST_TYRE_OBSERVATIONS_V1.md)
defines the normalized Hansen density and inference boundary.

Inputs are R021's fuel-corrected pace PROXY with the unchanged fuel PRIOR and
R022's sealed Gaussian-trained group posterior/Q/R. Training is Bahrain and
Australia; Miami supplies diagnostics; Monza and Singapore supply development
test scores. These are previously inspected development races. Permanent
benchmark telemetry is excluded.

Shape selection uses a frozen finite training likelihood grid. Held-out
observations update conditional latent state particles only; global parameter
draw weights remain fixed. The selected nu=4, skew=.5 sits on grid boundaries.
Saved predictive ensembles retain Monte Carlo seeds, group draws, origin/target
keys, raw intervals/PIT and CRPS/RMSPE. The verifier hashes every artifact and
recomputes CRPS from the saved draws.

Recommended scope: compare robust latent pace predictions against the matched
Gaussian control. Fixed fuel priors, Gaussian-trained parameters, particle
approximation, finite-ensemble CRPS bias, reused development tracks and raw
coverage below nominal 90% restrict interpretation. No proprietary tyre state,
joint skew-t posterior, exact calibration or production deployment is claimed.

Run from the checkout with fresh output directories:

```powershell
.venv/Scripts/python.exe -m apexsim.cli robust-tyre-demo --baseline .cache/tyre-study-final-20261011 --output .cache/robust-tyre-new
.venv/Scripts/python.exe -m apexsim.cli verify-robust-tyre-study .cache/robust-tyre-new
```

Use `--profile smoke` with a smoke baseline for execution checks; smoke cannot
close a research task. Large posterior/ensemble files stay in ignored local
storage; compact manifests and results are version controlled. Research runs
require the preceding sealed R021/R022 artifacts.
