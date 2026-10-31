# R034 equation-to-code map

Adaptation: matched-horizon reporting of existing accepted R030 equations.

| Quantity | Equation | Implementation | Check |
|---|---|---|---|
| Frozen physical acceleration | dv/dt=p*u/v-[d_open+d_extra*(1-z)]*v²-r | `open_loop_errors.predict_horizon` | Independent scalar/DOP8532525 paths |
| Causal slope | sum((t-mean(t))*v)/sum((t-mean(t))²), five past samples | `LongitudinalSection.initial_acceleration_mps2` | Future-target perturbation; scalar audit |
| Future-node MSE | sum((v_pred-v_target)²)/n_future | `open_loop_errors.error_record` | Hand case MSE5; independent scalar metrics |
| Speed-integral error | trapezoidal integral(v_pred-v_target)dt | `error_record` | Hand case2.5m; independent scalar sum |
| Hierarchy | equal sections/lap, laps/driver, drivers/event, events/split | `hierarchical_scores` | Unequal-density hand case; independent nested means |
| Support | horizon<=frozen duration | `horizon_grid`, `open_loop_study.compute` | Exact endpoint/short section; complete600-case ledger |

The initial target is not scored. Held controls use their left endpoint. Target
endpoint interpolation is evaluation-only. No equation here creates missing
steering, continuous-stint observations or an all-regime calibrated vehicle.
