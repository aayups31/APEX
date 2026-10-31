# R034 matched forecast reporting component

Research-only error accounting for frozen R030 section forecasts, not a new
dynamics model. [Evidence and limitations](../verification/open-loop-errors-report.md).
Inputs: accepted R033 native observation snapshot, accepted frozen R030 model,
five native causal speed samples and left-held recorded throttle/DRS.

Outputs: exact.5/1/2/3s target-matched paths, future-node speed errors, endpoint and
speed-integral errors, hierarchical split/track/speed/DRS summaries, complete source
lap/stint catalogs and explicit abstentions. Interpolated target endpoints are
RECONSTRUCTED; model trajectories are SIMULATED. Full physical lap/stint errors
are UNKNOWN/null. All regimes outside the frozen full-throttle/straight/high-speed
section domain remain unavailable.

No training, selection, promotion or uncertainty calibration occurs. Development
event reuse, source gaps, reconstructed endpoints and unavailable steering/body
state limit interpretation. Constant-speed sampled-lap diagnostics are explicitly
unvalidated. A sealed report can be moved and numerically regenerated without
network access; original public source acquisition is not part of the verifier.
