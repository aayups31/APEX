# R039 two-node tyre thermal research gate

West et al. (2020) motivate separate tread and carcass heat storage. APEX uses
a linear lumped adaptation with explicit effective-axle priors.
[Primary paper](https://ifatwww.et.uni-magdeburg.de/ifac2020/media/pdfs/0335.pdf)

Temperatures use kelvin, capacities J/K, conductances W/K, and heat rates W.
The tread receives a specified heat rate, exchanges heat with the road and
conducts heat to the carcass. The carcass receives its own specified heat rate
and exchanges heat with air. Internal conduction cancels in the total energy
balance. Exact piecewise-constant integration returns the integrated exchanges.

The R037 replay adapter assigns simulated lateral slip dissipation to each
effective axle tread and allocates 30% of simulated rolling resistance power
to the carcasses by axle normal-load share. Bath temperatures and all thermal
parameters are fixed priors. The axle approximation cannot resolve individual
tyres. The adapter consumes left-edge states and held commands without feeding
temperatures back into vehicle dynamics. R040 owns wear coupling.

Acceptance uses hand-computable isolated heating, equal-temperature equilibrium,
adiabatic exchange, warming and cooldown, an independent numerical integration,
and all four verified nominal R037 learned five-lap replays. Require finite
positive temperatures, per-interval balance error at most 1e-6 J, and maximum
temperature difference against the independent solver at most 1e-6 K.
This validates heat balance and conditional response under supplied priors.
Temperature and heat-partition calibration require measured thermal data.
