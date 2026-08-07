# Assumption Register

Every material assumption needs an owner, evidence level, uncertainty range, tests and retirement condition.

| ID | Assumption | Current V0 value | Evidence | Risk | Retirement condition |
|---|---|---:|---|---|---|
| A001 | Generic dry mass | 800 kg | public rules-level prior | medium | ruleset adapter + calibrated era config |
| A002 | Max power proxy | 740 kW | broad engineering prior | high | fit envelope with uncertainty |
| A003 | Drag/downforce areas | generic | synthetic only | high | track/session calibration |
| A004 | Tyre grip curves | hand-shaped | synthetic only | very high | stint/lap calibration and sensitivity |
| A005 | Tyre temperature | latent proxy | unobserved | high | never label as measured; infer distribution |
| A006 | Fuel burn | generic distance/throttle | unobserved | high | race-distance constraint fit |
| A007 | Energy store | generic 4 MJ proxy | incomplete public observability | very high | keep scenario-only or replace with latent model |
| A008 | Dirty-air loss | exponential gap factor | literature/engineering prior needed | high | causal/sensitivity study |
| A009 | DRS effect | generic drag reduction | engineering prior | medium | straight-line calibration |
| A010 | Pit loss | combined time block | transparent placeholder | high | circuit pit path + event fit |
| A011 | Overtake success | stochastic heuristic | synthetic only | very high | historical context model |
| A012 | Flag speed factors | fixed multipliers | placeholder | high | rules/state calibration |
| A013 | Reliability | aggregate hazard | synthetic only | high | use only uncertainty scenarios |

Add rows before adding magic numbers. Never delete retired assumptions; mark them superseded.
