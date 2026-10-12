# Conditional robust tyre observations v1

R023 is an independent ADAPTATION. The standardized distribution follows
[Hansen (1994)](https://www.ssc.wisc.edu/~bhansen/papers/ier_94.pdf) and the
[official arch implementation](https://bashtage.github.io/arch/_modules/arch/univariate/distribution.html).
The density/CDF/quantile implementation was reviewed; this is not a reproduction
of Cappello's proprietary experiment or a claim of full-paper review.

## Distribution and units

For nu > 2 and |lambda| < 1, define

```
c = Gamma((nu+1)/2) / (sqrt(pi*(nu-2))*Gamma(nu/2))
a = 4*lambda*c*(nu-2)/(nu-1)
b = sqrt(1 + 3*lambda^2 - a^2)
s(z) = 1-lambda if z < -a/b, otherwise 1+lambda
f(z) = b*c * [1 + ((b*z+a)/s(z))^2/(nu-2)]^(-(nu+1)/2)
```

The standardized random variable Z has mean zero and variance one. For source
fuel-corrected pace y and latent pace x (seconds), the likelihood is
`f((y-x)/sqrt(R))/sqrt(R)`. R is the Gaussian-trained observation variance in
seconds squared; changing shape preserves its scale interpretation. The latent
transition remains `x_(t+1)=x_t+d+Normal(0,Q)` with d in seconds/lap.

| Mathematical element | Code in `apexsim.research.skew_tyre` | Independent check |
| --- | --- | --- |
| Normalized density | `SkewStudent.logpdf` | Quadrature mass, mean and variance |
| Piecewise Student-t CDF/inverse | `cdf`, `ppf` | Inverse consistency and symmetric Student-t limit |
| Weighted two-piece sampling | `sample` | Sample moments; local RNG isolation |
| Conditional particle likelihood | `particle_training_nll` | Past-only fitting and protected-event refusal |
| Per-drift causal state filter | `observation_forecasts`, `systematic_resample` | Future-target intervention; near-Gaussian comparison with Kalman control |
| Empirical ensemble CRPS | `empirical_crps` | Hand-calculated ensemble expectation |

## Inference boundary

The sealed R022 posterior, training Q/R and fixed fuel prior are retained. Shape
is selected only on Bahrain/Australia using the preregistered 12-point grid and
512 state particles. Each held-out segment uses 32 fixed posterior drift draws
with 64 conditional state particles per draw. Past observations update state
particles, without reweighting global group draws. This is modular/cut inference;
it is not a jointly refitted skew-t Bayesian hierarchy.

Initialization samples `x_0=y_0-sqrt(R)*Z` under a flat intercept prior.
Forecasts at horizons 1/3/5 are generated before their target observations enter
the filter. The Gaussian control uses exact conditional Kalman states, the same
posterior drift subset and matching origin/target keys. Both forecasts include
future process and observation noise. Seeds 11/23/37 represent Monte Carlo
replicates, not three independent datasets.

CRPS is `mean(|draw-y|) - mean(|draw_i-draw_j|)/2`, evaluated by a sorted
ensemble identity. Finite ensemble bias and particle approximation remain.
Intervals/PIT are raw predictive diagnostics; R022's separate validation
interval adjustment is not applied again here.

The selected nu=4, lambda=.5 lies at the frozen grid boundary. No continuous
shape optimization, test-driven grid expansion, measured tyre state, exact
nominal calibration or production promotion follows. The
[verification report](../../docs/verification/robust-tyre-forecast-report.md)
records the acceptance decision and all limitations.
