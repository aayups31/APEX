# Individual pace relative to contemporaneous peers

Screen the next hypothesis on the opened v24 cohort before requesting
telemetry for additional training windows. Use v28's matched wider field.
The target in seconds is the subject's change from its prefix median to
its target median less the observed change of matched peers. This is a
development diagnostic for an individual-car effect, including traffic
and driver choices.

Keep windows with a matched peer and at least 90 percent valid native
coverage on each of the three subject prefix laps. Within race, driver
and current stint, order by the first tyre age then original index. Keep
the earliest remaining twelve-age window and skip subsequent windows
whose ages overlap it. Resolve repeated reference pairs by the same rule.
Require input and outcome agreement on repeated current windows. Report
the number of retained physical windows and races.

Compare predicting zero individual deviation with two ridge models.
Use the three centered subject prefix paces, their median, first tyre
age, current relative compound indicators and v28's six current field
features for the timing model. Add the five native car-channel means
and their last-minus-first changes for the telemetry model. Fit each
with equal race mass, training-only scaling and ridge penalty 10.
Withhold the entire test race. No race identifiers or future-field
measurements enter the predictors. Compare absolute individual-deviation
error averaged equally over races. Count race wins against each baseline.

Advance to expanded telemetry training if the telemetry model beats
both baselines in macro error and beats timing alone in more than half
of represented races. Otherwise end this particular aggregate-channel
candidate and use the failure distribution to choose the next data
requirement. This auxiliary screen cannot qualify an R041 forecast.
