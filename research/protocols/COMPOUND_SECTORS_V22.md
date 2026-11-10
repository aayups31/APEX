# R041 native sector redistribution

The v21 residual audit shows that a hindsight correction limited to the 20
incomplete cases still leaves 13 failed races. Test native split timing as a
distinct signal on the same 392 cases and 28 already opened sources.

Use the three current prefix, three reference prefix and three reference
target laps. Bind each by native driver and exact frozen lap end. Guard race
identity and archive hash before feature extraction. All selected laps must
end by the original forecast cutoff. Read native sector durations from the
same timing records that supplied each lap. Require all three positive finite
sectors to sum to native raw lap duration within 0.05 seconds. Preserve missing
laps and reject ambiguous clock matches. Never fill from a later lap.

Use the first two sector shares of summed sector time. The third share is
determined by those two. Append the last minus first current prefix shares
and the differences of current mean shares against each of the two reference
groups. Each group needs three valid splits. Use zero when a required group
is missing and append the three group support flags. This produces nine inputs
and removes total lap duration from the new features.

Fit one unchanged weighted ridge with alpha 10 on the corrected v21 control
inputs plus these features. Use whole-race exclusion, training-only scaling,
three predicted laps and the existing two-second bound. The saved corrected
control is the matched comparison. Keep all existing paired-label race gates,
including negative controls and per-race baselines. Record full support,
independent checkpoint replay, regression results and every failed race.
No model or threshold search. Failure ends this candidate. Fresh confirmation
requires a complete development pass and its own frozen acquisition protocol.
