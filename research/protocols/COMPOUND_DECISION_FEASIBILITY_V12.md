# R041 decision semantics and feasibility review (v12)

The v10/v11 shared decision is mathematically unsatisfiable for the opened 2024 Monza fold. Among 13 comparisons, the difference of medians yields one observed crossing and the median of paired differences yields zero. Primary recall requires at least one positive prediction. The paired negative control requires exactly zero. This contradiction holds for every possible shared prediction vector, regardless of model, compute or training sample size. Across the complete 392-case cohort the observed binary labels disagree on 22 cases.

## Forward decision

Preserve the rejection of v10/v11. For a new development evaluation predict the three age-matched current lap times once, and compute each label and its crossover from those same three predicted laps using the corresponding observed-label formula. A crossover requires opposite signs beyond 0.15 seconds at both ends. This changes the output contract and is therefore a new experiment. Preserve both baseline comparisons (including the original scalar reference baseline for both labels), 50% precision and recall, zero false alarms on negative controls, all 392 cases, whole-race splits, at least two informative races and the original forecast time. Additional comparator: each label's own reference persistence. Record every failed gate separately.

## Registered experiment before scoring

Predict each of the three current target laps as its corresponding known prefix lap plus a common drift. Use the median observed change in the three-lap median from training windows of the same current compound. Give each training race equal weight by first taking its median across unique current windows, then the median of race medians. Exclude the complete forecast race. Cap drift magnitude at 2 seconds. Fall back to zero drift when fewer than three training races support the compound. Also evaluate zero drift as a fixed comparator. No hyperparameter search or tuning against these scores.

Independently check feasibility by substituting observed target laps only in an explicitly labeled oracle diagnostic. Require exact reconstruction of both target definitions and perfect event decisions in that diagnostic. The oracle cannot qualify a model. Confirm production remains disabled and the actual candidate qualifies only if every supported event passes. If it fails, keep fresh race outcomes sealed and R041 open. Physical tyre wear remains unknown.
