# Fuel-corrected latent pace v1: independent Gaussian adaptation

Classification: ADAPTATION, tasks R021/R022. Paper motivation:
[Cappello and Hoegh, arXiv:2512.00640v1](https://arxiv.org/abs/2512.00640).
Only the abstract was reviewed. These are APEX's own Gaussian equations; the
paper's Austrian/Hamilton/skewed-t case has not been reproduced. The legacy
`state_space_tyre.py` remains an educational starter, outside this causal study.

## Symbols and units

| Symbol | Unit | Code meaning |
| --- | --- | --- |
| l | race lap | Source `lap`, positive integer |
| T_l | seconds | Native `observed_s`, FastF1 parsed source |
| m_l = 105 - 1.4(l-1) | kg | Fixed fuel PRIOR, rejected if negative |
| y_l = T_l - .030 m_l | seconds | `corrected_s`, PROXY |
| x_l | seconds | Latent fuel-corrected pace, MODEL_ESTIMATE |
| d | seconds/lap | Compound or hierarchical latent pace drift |
| Q, R | seconds squared | Process/observation variance, training estimates |

Each contiguous eligible segment resets. The state equations are
`x_(t+1) = x_t + d + w_t`, `y_t = x_t + e_t`, with independent
`w ~ N(0,Q)`, `e ~ N(0,R)`. Conditioning on the first observation with a flat
intercept prior gives `x_0 | y_0 ~ N(y_0,R)`.

Predict `a = mu+d`, `P_pred=P+Q`, `S=P_pred+R`, `K=P_pred/S`;
update `mu=a+K(y-a)`, `P=(1-K)P_pred`. At an observed origin t,
`y_(t+h) ~ N(mu_t+h*d, P_t+h*Q+R)` before the target is observed.
No numerical innovation clipping or whole-sequence baseline is used.

## Independent likelihood check and fit

For a segment of n+1 observations, set `z_i=y_i-y_0`, i=1..n,
`C_ij=Q*min(i,j)+R*I(i=j)+R` and `v=(1,...,n)`.
The exact marginal drift likelihood is proportional to
`N(d; (v'C^-1 z)/(v'C^-1 v), 1/(v'C^-1 v))`. A Kalman recursion obtains
this same quadratic in linear time. An independent direct covariance/GLS
fixture checks its mean and variance. Training-only marginal likelihood fits
the three compound drifts, Q and R with preregistered bounds and fixed starts.

Persistence and last-three-observation trend share every origin/target with the
state model. Their point errors are the primary comparison. Their reported
Gaussian NLL/intervals borrow the fitted state model's variance; those baseline
intervals are an explicit approximation, not independently calibrated models.

## Hierarchical posterior

`d_s = beta + c_compound + t_track + u_driver`. Segment likelihood means have
known variances from the preceding exact likelihood, conditional on training Q/R.
With design X, likelihood variances V and diagonal prior precision D,
`Lambda=X'V^-1 X+D`, `b=X'V^-1 y+prior_natural`, and
`theta | tau,y ~ N(Lambda^-1 b, Lambda^-1)`.
The sampler uses a Cholesky precision solve. Each group variance conditional is
`IG(3+n_group/2, prior_scale+sum(effect^2)/2)`; priors/scales are frozen in
the protocol. Proper priors regularize otherwise confounded additive effects.
Population and supported drift combinations receive split-chain R-hat diagnostics;
group-variance diagnostics are also reported. R-hat alone is not a proof of
identification or a substitute for future broader sampler diagnostics.

For unseen groups, draw conditional zero-mean effects using each posterior group
variance. Predictions integrate drift, conditional state, and observation noise.
The global posterior stays fixed in held-out races. Each drift draw runs its own
causal state filter, without reweighting global parameter draws by held-out
prefix likelihoods: this is a modular/cut-feedback predictive approximation,
not full Bayesian updating on the test prefix.

Raw predictive quantiles and mixture NLL/PIT remain separate from the validation
adjustment: Miami fixes a horizon-specific order statistic of `abs(error)/sd`;
Monza/Singapore receive `mean +/- scale*sd`. Parameter credible intervals remain
unmodified. Correlation and distribution shift preclude a guaranteed 90% test
coverage claim. Numerical evidence and limitations are in the verification report.
