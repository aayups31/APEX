# R036 conditional imitation equation-to-code map

Research ADAPTATION of finite dataset aggregation, Ross/Gordon/Bagnell2011,
[PMLR15 paper](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf), Algorithm3.1.
Expert-labelled visited states are collected, supervised models fitted, a learner
executed on training conditions, and its newly labelled states aggregated once.
The paper's asymptotic guarantees and racing-game magnitudes are not reproduced.

| Quantity | Equation/convention | Code/check |
|---|---|---|
| Expert residual | (L+K*v²)*(kappa(s+tau*v)-kappa(s)), rad | `imitation_driver.expert_residual`; independent scalar label |
| Understeer prior | K=m/L*(b/Cf-a/Cr) | R035 prior, not fitted physical parameter |
| Local observation | current body state, wrapped velocity-heading error, known map preview, previous applied steering | `observation`; scalar audit and rigid-frame invariance |
| Weighted mean | mean_j=sum(w_i*x_ij)/sum(w_i) | `fit_policy`; hand weighted fixture and independent scalar sums |
| Weighted scale | sqrt(sum(w_i*(x_ij-mean_j)²)/sum(w_i)); constant-feature scale1 | train-only; independent audit |
| Polynomial design | [1,z_j,z_i*z_j for i<=j] for degree2 | `design_matrix`; hand order fixture,45 coefficients |
| Ridge objective | sum(w_i*(Phi_i*theta-y_i)²)+alpha*sum(theta_j²,j>0) | augmented NumPy SVD, independent pivoted QR |
| Bounded influence | delta=delta_R035+clip(predicted_residual,+/-.2rad) | `policy_command`; intervention exposed, no state clipping |
| Applied controls | R035 angle/rate/force equations at actual applied steering | `apply_steering`; accepted-controller parity tests |
| Collection weights | equal rounds, equal balanced episodes, equal rows within episode | `training_arrays`; density/role tests |
| Validation choice | minimum complete equal-driver/lap station MSE, declared tie rules | `fit_imitation_study`; reconstructed choice audit |
| Tracking gate | sqrt(mean_driver(mean_lap(MSE_final)) / corresponding R035 mean)<=.9 | `improvement_gate`; hand gate/case-omission tests |
| Physical rollout | accepted R032 six-state RK4/implicit load equations | `rollout_policy`; independent bisection/DOP853 |

The student predicts no future physical state; it maps current local observations
to a steering correction. Teacher forcing, autonomous closed-loop control and
held-action physical replay remain separate evidence. The model never receives
an expert label during inference. All demonstration labels are SIMULATED and
cannot establish observed human actions or real-car parameter identification.
