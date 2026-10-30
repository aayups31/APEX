# ADR0007: complete R027/R028 before returning to R030

Date:2026-10-30. Status:accepted, explicit user scheduling decision.

The default master-guide priority selects R030, the earliest eligible P0 task.
The user explicitly requested: "finish 27 and 28 then we go back to our sequence"
and frequent commits/pushes. Complete the two dependent forecasting explanation
tasks as one bounded research slice, then restore the normal R030 sequence.

R025 fitted models and R026 development evaluation satisfy their dependencies.
The [preregistered study](../../research/protocols/FORECAST_EXPLANATIONS.md) must
test faithfulness and constraint validity, preserve unsupported/abstaining cases
and avoid fitting against the evaluation data. It adapts paper ideas to public
proxy targets; it does not reproduce proprietary-data TIME/CausalImpact results.

"Feasible" is explicitly conditional on declared kinematic/proxy equations and
training marginal support. Real actuator/friction/path feasibility and causal VSC
effects remain UNKNOWN pending vehicle and closed-loop validation. Research-only
code cannot enter the race kernel or planner through this scheduling exception.
Foundation R1/kernel R0 remain unchanged. All prior frozen protocols remain valid.
