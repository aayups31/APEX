# Protocol — Heilmeier Race Simulation and Monte Carlo

## Scope
Lap-wise full-field simulation with fuel, tyres, pits and overtaking, extended with probabilistic lap/pit variation, starts, incidents, failures, FCY and safety cars.

## Work plan
1. Crosswalk every APEX race transition. 2. Estimate residual lap-time distributions after removing fuel/tyre/pit effects. 3. Fit pit-duration and start-loss distributions. 4. Build incident/failure hazard models. 5. Implement safety-car gap compression and restart. 6. Verify Monte Carlo convergence. 7. Compare strategy expected value, variance, CVaR and finishing-position distribution.

## Acceptance
Held-out distribution calibration, event-rate calibration, reproducible seeds, stable strategy ranking with increasing samples and no use of future event knowledge.
