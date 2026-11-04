# R041 direct crossover event head, v6

Research foundation R1 and production R0; R041 open. Follow ADR 0010 and preserve
all v1-v5 failures. Use the eight opened 2025 events as development data.
Reuse v4's timestamp-checked completed-reference cohort, fixed clean/dry filters,
12 consecutive common ages in disjoint blocks, nine-lap horizon, and 0.15 s
sustained three-lap median sign margins. Keep both label definitions.

## Two distinct outputs

The pace head is v5's weighted ridge, alpha 10, refitted on eight development
events. The event head is balanced logistic regression, C=0.1, decision score
threshold 0.5, max_iter=1000. Fit StandardScaler on development inputs only,
without sample weights; use unit total weight per unique current-stint/age
window when fitting the classifier. For each training case, include both binary
crossover labels with half the case weight. Class balancing is scikit-learn's
declared balanced option. Save scaler and logistic coefficients as plain JSON
so frozen inference needs no fitted-library object.

Inputs are the six v5 covariates, plus absolute primary prefix contrast,
primary prefix contrast times completed-reference persistence contrast,
the completed-reference persistence crossover indicator, and absolute
pairwise prefix contrast. Every input predates or equals forecast time;
future current-stint pace and traffic are never prediction inputs.

Development screening compared C in {0.1,1,10}, thresholds {0.3,0.4,0.5,0.6,0.7},
and small forest baselines with/without historical field context. Save the
reproducible logistic grid. Select highest minimum of precision and recall
under both label definitions across pooled leave-one-event-out predictions;
break ties by lower C, then threshold closest to 0.5. C=0.1/threshold=0.5 gives
primary 27/48 observed matched with 38 predictions; pairwise 22/44 matched.
Individual development failures, especially Hungary, remain explicit.

Report event score, event decision and pace point prediction separately. Record
how often the event decision differs from thresholding the point prediction.
Balanced scores and training residual radii are not calibrated confidence.

## Fresh split and acceptance

Freeze code, data hashes, selection evidence and parameters before opening
Netherlands 2025 round 15 (session 9920, meeting 1267) or Singapore round 18
(session 9896, meeting 1270) lap outcomes. Only session metadata was inspected.
Preserve raw five-table OpenF1 archives, request/retrieval metadata and hashes;
verify permanent benchmark reservations before acquisition.

In EACH fresh race and under EACH label definition: nonzero observed and
predicted events, at least half of observed and half of predicted events
matched by the frozen event head, and pace-head MAE no worse than BOTH original
contrast persistence and completed-reference persistence. Report 2024-prior
error, RMSE, uncertainty coverage, widths, compound breakdowns and disagreements.
These numeric thresholds are unchanged; event decisions now have an explicit
event-specific loss rather than thresholding the mean pace forecast.

No retuning after fresh outcomes. Pass requires saved results, exact replay,
independent native/scalar audit of both heads and gates, causal mutation tests,
full applicable verification and CI. Absent reference or unsupported compound
means abstain. Roll back by retaining R041 open and preserving every attempt.

Sources and effective-pace truth labels follow v4/v5. Public source and terms:
https://openf1.org/ . Logistic implementation reference:
https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html .
