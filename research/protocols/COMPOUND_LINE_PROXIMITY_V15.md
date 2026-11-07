# R041 timing-line proximity study

Test whether nearby cars at the timing line explain some of the nine-lap
forecast error. V3 relied on sampled intervals and lost coverage under a
clean-air restriction. Here both providers supply native lap clocks. A prior
crossing by another driver measures proximity at one line. Its interpretation
includes lapped traffic, pit-lane timing and incomplete provider records.

Freeze the v11 cohort, v13 nominated model inputs, training weights, ridge
penalty, lap bounds and v12 gates. The matched control is the sealed v13
nominated result. Add exactly nine features to its model. For each of three
windows (current prefix, reference prefix, reference target), compute the
median gap, last minus first gap, and fraction of gaps at most 1.5 seconds.
For each subject lap use the latest strictly earlier recorded finish by a
different driver across all lap numbers. Cap at ten seconds and use ten when
there is no recorded crossing in that lookback. Use native start plus measured
duration. Exclude missing clocks or invalid durations. Require exact subject
driver and clock association to each sealed lap. Reference observations must
already be complete by the original forecast time. Keep all cases.

Train a single augmented candidate with each complete evaluation race removed.
Compare against the saved control on the same 392 comparisons in 28 opened
races. Report all supported event gates, macro error, gains and losses, and
negative-control alarms. No tuning or new race acquisition on failure.
Qualifying on development permits only a separately frozen fresh confirmation.
