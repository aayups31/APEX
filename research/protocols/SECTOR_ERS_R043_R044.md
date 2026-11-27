# R043 sector energy and R044 shrinking horizon

APEX research foundation R1 and production kernel R0. Adapt the
energy allocation and shrinking-horizon ideas in Duhr et al.
[Primary paper](https://doi.org/10.1109/TVT.2023.3237388).
Reuse the Fieni model's sign convention and MJ units. This fixture
uses supplied mechanical work opportunities and synthetic time costs.
It establishes numerical behavior under known bounds.

Each sector supplies duration, a wheel-side power limit, available
mechanical work and a mode (deployment, harvest or coast). Bound wheel
work by both duration times power and available work. With deployment
efficiency 0.8, removing one MJ from storage delivers 0.8 MJ at the
wheels. With harvest efficiency 0.8, one MJ of braking work stores
0.8 MJ. The unconverted energy is a loss. Require finite admissible
states, continuous sector-boundary charge and terminal minimum charge.
The state is monotone within a fixed-mode sector.

R043 solves the linear time surrogate using linear programming. Verify
all state and terminal bounds by replay. Compare the nominal six-sector
fixture with exhaustive enumeration on a 0.25 MJ stock grid, including
all reachable states on the grid and a fixed no-action baseline. Require
objective agreement within 1e-9 s and reject an infeasible terminal target.

R044 applies only the first action, observes actual charge, then shrinks
the horizon. Forecast sector opportunities begin nominal. A loss of
half the first braking opportunity and a reduction in the final
deployment opportunity are revealed at entry to those sectors. Keep
future changes hidden from the controller. Compare with the nominal
open-loop actions restricted to the observed local physical limits.
Compare both with a full-information optimum for context. Require
nominal replay to match the nominal optimum, all disturbed feedback
actions to remain legal, the terminal bound to hold, and the disturbed
fixed policy to miss the terminal bound. Record wall-clock timing and
require each feedback solve to finish in five seconds in the fixture.
If no plan can meet the current terminal bound, report infeasibility.

The objective, efficiencies and constraints are synthetic. Production
use and season-specific regulations need separate validation.
