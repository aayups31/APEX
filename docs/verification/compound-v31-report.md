# R041 traffic and crossover-aware forecasts

The corrected nomination/practice baseline still passes 9 of 24 supported
races. Both new candidates were evaluated on the same 393 comparisons
with the whole test race excluded. Four additional races have zero eligible
comparisons.

| Forecast | Races passing | Race-averaged absolute contrast error |
|---|---:|---:|
| Nomination/practice ridge | 9 / 24 | 0.444 s |
| Timing-line proximity added | 8 / 24 | 0.449 s |
| Timing-line and intermediate proximity added | 9 / 24 | 0.465 s |
| Shared shift trained on pace error | 9 / 24 | 0.447 s |
| Shared shift trained on pace and crossover error | 7 / 24 | 0.455 s |

## Traffic inside the lap

391 comparisons have complete prefix-sector splits. In 357 cases, at
least one intermediate point in the current prefix includes a preceding
car within ten seconds. The richer feature set gains two races and loses
two against the baseline. Timing gaps are an approximation
of traffic exposure. A crossing supplies a discrete timestamp, and
sector observations require a complete, reconciled peer lap available at
the case's forecast cutoff.
[Protocol](../../research/protocols/COMPOUND_SECTOR_TRAFFIC_V30.md),
[timing links and forecasts](compound-v30-development.json).

## What a shared lap shift could recover

An outcome-aware diagnostic checks every decision boundary and the
intervals between them over shifts legal under the two-second lap bound.
Shifting the three prefix laps together could reproduce both observed
decisions in 386 of 393 cases. For the ridge forecast's lap shape, it
could reproduce both in 377. For either shape, no race is ruled out by
individual-label recall reachability alone. This calculation does not
account for joint race gates on precision and pace error.
[Per-case reachability](compound-common-shift-audit.json).

The fitted crossover-aware objective lowers the number of race-label
recall failures from 10 to 9 compared with its timing-only control.
It raises precision failures from 10 to 11 and false-alarm failures
from four to five. The two losses are evaluated at the same crossover
boundary and feed the same three-lap forecast interface. A shared shift
can generate most observed decisions given the answers. The modeled
inputs and loss have inadequate accuracy at forecasting that shift.
[Protocol](../../research/protocols/COMPOUND_DECISION_LOSS_V31.md),
[fold checkpoints and gate audit](compound-v31-development.json).

## Remaining evidence gap

The public archives reviewed so far give tyre allocation, tyre age, timing,
driving channels and weather. An individual, time-stamped tyre pressure
or temperature series with usable coverage remains unverified. The FIA
publishes event prescriptions and summaries of compliance checks.
[Archive feed inventory](https://f1archive.org/docs),
[OpenF1 schema](https://openf1.org/docs/#car-data),
[earlier input-source review](compound-v29-report.md).

The next candidate needs an observable car-specific input with demonstrated
predictive value for the pace shift. Qualify it on the unchanged race gates
before opening fresh confirmation sessions.
