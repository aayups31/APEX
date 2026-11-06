# R041 v13 predeclared nomination experiment

Use only the opened v11 392-case cohort and all 28 source identities. Join the
two nomination inventories by event, validate uniqueness, three increasing
C-numbers and issue date before forecast day. These are pre-race announcements.
Physical wear and verified per-set construction remain unknown.

Predict three current target laps jointly relative to the median current prefix.
Use the full v11 causal trajectory features, three centered prefix laps, three
reference target laps relative to the current prefix median, reference compound
indicators and season indicators. The primary model adds one-hot indicators for
each reference/current nominated C-number and the same indicators interacted
with season. Treat equal C-numbers across years as partial pooling assumptions.
Use fixed ridge alpha 10 with weighted train-only scaling, equal race weights and
duplicate-target adjustment. Clip each lap's change from its corresponding
prefix to +/-2 seconds, logging saturation. A matched ablation removes only
the C-number features. No tuning or selection between the two after evaluation.

Keep v12's whole-event splits, two crossover readouts, both persistence
comparisons plus label-specific reference, 0.15-second margin, precision and
recall >=50%, zero control false alarms and two informative races. Count every
case. The primary must pass every supported race before separate prospective
confirmation. Reject this hypothesis if it fails. Preserve all prior decisions.
