# R041 contemporaneous field pace

Use only the opened v24 development cohort and its existing clean, dry,
fuel-adjusted timing archives. Test whether the recent change in pace of
other cars helps the nomination/practice ridge anticipate a crossover.
Prior completed equal-age windows measure a different quantity. Here each
peer contributes at its own tyre age at the subject's clock.

At each of three clocks (end of current prefix, reference prefix and
reference target), take each other driver's most recently completed clean
lap. Require its end to be at most 150 seconds old and its most recent six
tyre ages to be continuous in that stint with increasing end times. Take
the change from the first three-lap median to the last three-lap median.
For the whole field and separately for peers on the subject stint's
compound, append the median change, its median absolute deviation and
log(1 + driver count). Use zero for empty groups. Fit the same weighted
three-output ridge and bounds as v24, holding out the entire race. Retain
all 393 forecasts and all original per-race gates. Compare with the
frozen nomination/practice ridge. Publish support, forecasts and replay.

As a separate diagnostic of the value of knowing the field's future,
match those current peers to their most recently completed clean lap at
the end of the subject target. Require the same stint, a fresh end within
150 seconds, continuous ages through that lap and all three late laps
after the forecast. Measure the change in each matched peer's three-lap
median between the two clocks. Append the same six summary features to
the causal model and evaluate by held-out race. This deliberately uses
future peer outcomes. Never use it for qualification or as a mathematical
bound. If only this diagnostic improves, investigate whether the future
field shift is predictable before committing to a new forecast family.
Fresh confirmation requires the causal model to pass the development gates.
