# R041 driver-control transfer diagnostic

Use the previously counted direct different-compound windows with at least
six prior controls. Verify their exact counts per race against the v25
support inventory. Subtract the median of prior same-compound paired lap
differences from the target difference, orienting all gaps from the harder
to the softer compound. Use the two relative compound identities as the
pair key. Fit a median adjusted target gap within each other race and
take the median of those race medians. Fall back to zero with no training
race for the pair. Restore the current pair's causal driver offset when
predicting the raw future gap. Compare absolute error against the prior
offset alone and the observed three-lap prefix difference. Report each
race, macro-average error, coverage and fallback counts. This is an
auxiliary transfer test of relative compound gap across drivers and races.
The full 393-case within-driver crossover task retains its original gates.
