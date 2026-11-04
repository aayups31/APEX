# ADR 0011: Prospective compound confirmation includes explicit negative controls

Status: accepted for the new v9 experiment; no retrospective gate changes.

The v8 Qatar failure remains a failure. It is now opened development evidence,
not an untouched test, and cannot be removed from the v8 panel. Bounded v9
qualifies for prospective testing under its registered nested development gate;
it still fails several development events and is less accurate on average than
the unbounded ridge comparator. Its proposed benefit is limited learned influence.

For a separately frozen v9 panel, require at least two fresh informative races
with observed crossovers under both label definitions. Each must satisfy the
existing >=50% precision/recall and both-persistence pace gates. Additional
supported races with no observed crossover are negative controls: they must
have zero predicted crossovers and pass the same pace gates. They cannot supply
positive crossover evidence. Empty cohorts are inconclusive, remain reported,
and cannot replace a supported failed event. Every supported race must pass;
no result-dependent substitution or threshold change is allowed.

This separates evidence of finding an event from evidence of avoiding a false
alarm. The separate v9 protocol freezes all four race identities in advance.
No change is made to v1-v8 claims, cohorts, results or historical acceptance.
Failure or inadequate prospective support leaves R041 IN_PROGRESS. A pass is
limited to conditional public pace/event forecasting and makes no production
promotion, physical wear or causal compound claim.
