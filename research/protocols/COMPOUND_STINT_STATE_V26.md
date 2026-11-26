# R041 sequential stint pace experiment

Use the 393 corrected v24 development cases and the original whole-race
exclusions, two crossover definitions, error baselines and pace bounds.
Use the Cappello and Hoegh stint reset and asymmetric lap-noise ideas as
a model adaptation for APEX's longer horizon. Keep the existing fuel
correction and use only current-stint observations available at the cutoff.
Source: https://doi.org/10.1177/22150218261446170

Estimate prior drift from complete 12-lap reference histories in other
races. Deduplicate identical driver/stint/age windows, compute each
window's median pairwise slope, then the median slope per race and compound.
Pool all compounds if fewer than three training races support a compound.
Use the median of race medians as prior drift and their scaled median
absolute deviation (minimum 0.03 s/lap) as its standard deviation.
Estimate within-window lap noise by the scaled median absolute residual
from a robust line. Use the median per race followed by the median across
races, with a 0.10-second floor.

At each new window reset the latent pace to the first available current
observation with a flat offset grid of 61 evenly spaced points over plus
or minus three noise scales. Use 51 slope grid points spanning four prior
standard deviations either side of the prior mean with Gaussian weights.
Update both states jointly on each available current-history lap. The
observation distribution is 90% centered Gaussian and 10% Gaussian delayed
by two noise scales with twice the standard deviation. Forecast the posterior
mean pace including the expected observation delay. Score the bounded
three target-age predictions. Verify sequential inference against a batch
log-likelihood calculation and independently replay the race decisions.

Compare against a symmetric Gaussian observation control on exactly the
same grid and the saved v24 nomination/practice ridge. The asymmetric
model is the sole candidate. Report missed crossings and false alarms on
fuel-stable and fuel-sensitive labels. Only a complete development pass
opens prospective confirmation.
