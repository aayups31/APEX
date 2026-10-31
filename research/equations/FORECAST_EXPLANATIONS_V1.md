# R027/R028 equation map — public proxy adaptation

Sources: Todd et al. arXiv:2501.04067v1 sections3.5/4.2; Sood & Craven
arXiv:2102.11934v1 equations2–8. See the [frozen protocol](../protocols/FORECAST_EXPLANATIONS.md)
and its [numerical correction](../protocols/FORECAST_EXPLANATIONS_NUMERICS.md).
No proprietary Mercedes data, original TIME implementation or CausalImpact
causal-effect reconstruction is claimed.

| Symbol | Meaning / units | Code owner / source |
|---|---|---|
| x | causal eight-sample,14-field history, mixed declared SI/kJ | `ForecastWindows.dynamic`; R025 |
| s | immutable driver/compound/track one-hot categories | `ForecastWindows.static`; training vocabularies |
| f(x,s) | four-wheel direct1/3/5-sample raw forecast, kJ/sample | `FrozenForecastPredictor`; frozen R025 parameters |
| f+(x,s) | max(f,0), with count/largest correction logged | existing R025 nonnegative output contract |
| p=(g,[k1,k2)) | one of12 fixed feature-group/two-sample players | `PLAYERS`; preregistered design PRIOR |
| R(x,p,d) | replace p with the corresponding training donor block | `replace_players`; adaptation of TIME eq6/7 |
| delta[p,d,h,w] | f+(R(x,p,d))-f+(x), signed kJ | `temporal_explanation`; all raw predictions retained |
| A[p,h,w] | mean over four ranking donors of abs(delta), kJ | local model dependence, not loss/FDR/causal importance |
| Aaudit | same absolute response on four disjoint donor sequences | independent faithfulness half; never ranks the explanation |
| rho | Spearman(A,Aaudit) over12 players | tied average ranks; constant vector UNKNOWN/abstain |
| Dtop / Drandom | joint top-three vs16 random three-player deletion changes, kJ | separate audit-donor queries; seeded2728 |
| Itop / Irandom | reduction in distance to f+(x) after restoring three players | insertion starts from all-player donor replacement |
| a,b | speed factor and throttle offset, dimensionless | fixed11x5 finite scenario catalogue |
| v',ax',vg',omega' | a times original values, m/s,m/s2,m/s,rad/s | `transform_history`; uniform scaling |
| ay' | a2*ay, m/s2 | preserves ay=-v*omega |
| kappa | omega/vg, 1/m | unchanged curvature proxy; not a complete path proof |
| steer' | atan(3.6*kappa)=steer, rad | R024 wheelbase PRIOR3.6m |
| throttle' | throttle+b, dimensionless | reject outside[0,1], never clip |
| E'[t,w] | shared R024 sliding-energy proxy from transformed states, kJ | `estimate_wheel_tyre_energy`; mass900kg and frozen priors |
| F | equation/bound/load and training-marginal admissible histories | `history_violations`; conditional feasibility only |
| q | mean over matched three horizons/four wheels of f+, kJ/sample | not summed energy or power |
| tau | q0-max(.1*q0,.01kJ) | preregistered10%/.01kJ explanation goal PRIOR |
| c(a,b) | abs(a-1)/.2+abs(b)/.2 | dimensionless L1 scenario cost, exact decimal tie handling |
| C* | admissible catalogue candidates with q<=tau | same candidate must cross each seed for robust primary result |
| optimum | argmin over C* of (cost,a,b) | exhaustive55-candidate oracle only; no continuous/global optimality |

Four ranking and four audit donors are distinct training sequences of the same
driver/compound. Neither donor targets nor the origin's future actual energy
enter f, ranking, candidate construction or crossing. Future actual targets enter
only the explicitly secondary loss-increase diagnostic after explanation audit.

TIME's adaptive temporal localization, feature-order discovery and FDR procedure
are omitted. The fixed block grid and local output-change score are APEX's
adaptation. Global diagnostics average origins within event and then events;
500 sequence-cluster bootstrap draws condition on the four selected events.

Independent checks live in `forecast_explanation_audit.py`: scalar source and
constraint equations, complete finite-catalogue winner scan, SciPy Spearman and
independent coefficient/architecture reload. Hand fixtures cover exact sparse
lags, constant/irrelevant predictors, misleading donors, curvature/ay scaling,
unprojected wheel loads, finite minima/ties/impossibility and per-seed crossing.

Physical actuator/friction/thermal/path/race-control realizability remains
UNKNOWN. These retrospective histories are not validated executable controls.
