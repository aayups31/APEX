# R041 unpaired current-stint training

Before opening any additional outcome payload, test the hypothesis that eligible
current stints can supply more training examples within the already opened
28 races. Preserve v13 and its unchanged v12 evaluation cohort. No acquisition.

Use the original unique current windows for the control. For the extension add
disjoint twelve-age blocks from contiguous retained native laps using the same
provider-specific fuel, clean and dry filters as v11. Exclude additional blocks
overlapping an original current window for the same event, driver and stint.
Never bridge missing ages. Require increasing native end clocks. Inputs are the
first three current paces only, compound and start age, nominated compound and
season. Predict offsets for the last three ages from the median of the prefix.

Fit one weighted ridge (alpha 10) with three outputs. Give each event total
weight proportional to the mean number of windows per training event and
divide that weight uniformly among its unique windows. Scale features using
training weights. Include the three centered prefix paces, their median pace,
start age, relative-compound indicators, C-number indicators and season
indicators. Cap each projected change at two seconds. Average these laps
equally with the saved v13 nominated forecast for that case. Compare the
paired-only control and the expanded training set with identical features and
weights. Fix the expanded blend as primary. Each outer event, including its
unpaired windows, is excluded entirely from fitting and scaling.

Use all v12 per-event, per-label gates including both reference comparisons
and contrast persistence. Keep original races with no support visible.
Independently replay saved checkpoint forecasts, record comparison and
training counts, and preserve failures. Only a complete primary development
pass permits a new prospective confirmation. If the expanded sample fails,
stop this family of pace-only repairs before any fresh race is consumed.
