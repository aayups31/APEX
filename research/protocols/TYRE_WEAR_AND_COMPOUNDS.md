# R040 and R041 acceptance protocol

R040 uses the R039 left-edge tread temperature and the dissipative lateral
wheel work of the same held R037 controls. Per axle, remaining wear capacity
decays exponentially with sliding energy times an increasing temperature
factor. The rate and temperature scale are declared priors. Replay all four
nominal cases, check monotonicity, zero-energy invariance, and agreement with
the independently accumulated closed-form dose. Check warmer and higher-energy
counterfactuals. The model represents consumed fraction, with replacement
represented by initializing a new state.

R041 estimates compound pace offsets and nonnegative age slopes as effective
pace proxies. Public lap times cannot identify an energy-to-physical-wear
coefficient. Fit Bahrain, Australia and Miami only. Hold Monza and Singapore
out by event. Estimate compound contrasts within event-driver groups to remove
their intercepts. Compare a shared age slope against compound-specific slopes.
On held-out event-driver pairs with both compounds, compare predicted and
observed equal-age pace differences within overlapping observed age support.
Report contrast MAE, direction agreement, and sustained sign changes of
three-age median contrasts. A supported crossover requires both signs beyond
0.15 seconds in adjacent three-age windows, and prediction within five laps.
Acceptance requires a supported observed crossover in each held-out event,
at least half matched, and compound contrast MAE no worse than the shared
slope baseline on each event. Unsupported comparisons remain explicit.
