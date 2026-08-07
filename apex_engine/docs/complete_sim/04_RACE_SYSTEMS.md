# Race Systems

## Race state machine

```text
PRE_GRID → FORMATION(optional) → START → GREEN_RUNNING
                                  ↘ YELLOW / VSC / SAFETY_CAR
                                  ↘ RED_SUSPENDED
                                  ↘ FINISH → CLASSIFIED
```

The delivered V0 begins at START and supports scheduled flag states. Add formation, restart and red-flag procedure only after the green-race path is stable.

## Multi-car ordering

Primary progress is continuous race distance:

```text
total_distance = completed_laps × track_length + s
```

Finished cars are ordered by finish time. Active cars are ordered by distance. Retired cars are classified separately by completed distance/rules.

## Traffic model ladder

### V0

- gap to car ahead;
- following target-speed reduction;
- dirty-air downforce factor;
- DRS eligibility and zone;
- stochastic pass attempt.

### V1

- track-width and lateral lane choice;
- corner/straight pass opportunity model;
- defending line cost;
- closing speed and overlap;
- collision avoidance;
- pass success calibrated from historical contexts;
- uncertainty and driver interaction effects.

### V2

- learned interaction policy or graph model;
- multi-agent rollout with conservative safety constraints.

## Pit system

The delivered V0 transparently applies a combined pit-lane plus stationary time block. V1 must separate:

- pit entry path;
- speed limiter;
- lane travel;
- queue/stacking;
- stationary service time distribution;
- pit exit path and traffic merge;
- tyre change and warmup;
- penalties.

Never tune one pit-loss constant per race until predictions match. Model circuit pit-loss components and validate them independently.

## Tyre strategy

Strategy actions:

```text
stay out / pit now / pit in window
next compound
pace mode
energy-use mode
risk tolerance
```

Rules must be versioned. Do not bake current championship regulations into generic simulation code.

## Weather and surface

Weather is a schedule plus uncertainty. Surface state should eventually include:

- rainfall intensity;
- standing water;
- drainage/drying rate;
- dry-line formation;
- rubbering/grip evolution;
- local sector differences.

## Flags

V0 flag speed factors are explicit placeholders. V1 should represent:

- local yellow scope;
- delta-time compliance under VSC;
- safety-car queue and bunching;
- restart timing;
- pit-lane status;
- red-flag suspension and tyre/rule consequences.

## Reliability and incidents

Use low-frequency stochastic hazards only for strategy uncertainty. Do not imply individual driver/car reliability prediction from tiny samples. Separate:

- mechanical retirement hazard;
- collision/off-track hazard;
- damage severity;
- repair/pit consequence;
- race-control consequence.

## Determinism

For a fixed config, model bundle and seed, race outputs must be bitwise or numerically reproducible. Every random draw should come from owned generators—not global NumPy state scattered across modules.
