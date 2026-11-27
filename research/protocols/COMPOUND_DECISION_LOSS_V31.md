# R041 crossover-aware trajectory loss

The fixed-shape reachability audit leaves 386 of 393 observed decision
pairs reachable by shifting all three known prefix laps together.
Test whether learning the shift with a crossover-aware loss can recover
missed events. Use the nomination/practice inputs and whole-race
exclusion on the corrected cohort. No additional data.

A linear model emits one shift, applied to each prefix lap. Fit using
the original equal-race, duplicate-adjusted training weights and
training-only feature standardization. The timing objective minimizes
the mean of the squared errors of both future contrasts. Add an L2
penalty of 10 on the slopes with an unpenalized intercept.

Compare this timing-only control with a candidate that adds a squared
hinge penalty for crossing decisions, with a training margin of
0.15 seconds around the actual decision boundary. Only labels whose
initial contrast magnitude exceeds 0.15 seconds enter the hinge term.
Assign each outcome class half of the combined weighted hinge mass,
normalizing to the same total weight as the timing term. Multiply the
hinge term by one. The margin used to score decisions stays fixed.

Clip the shared forecast shift to two seconds, reconstruct both
decisions from the three lap predictions and run every existing gate.
Report both arms and compare against the frozen nomination/practice ridge.
Use an independent scalar checkpoint and gate replay. Only a complete
candidate pass permits fresh confirmation.
