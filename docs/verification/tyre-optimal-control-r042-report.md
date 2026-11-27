# R042 synthetic multi-lap tyre control

The synthetic benchmark passed its mesh convergence and pit decision checks.
APEX enumerated all 112 legal four-lap plans. Each plan can conserve or push
on each lap, and can replace the initial worn set once with a fresh soft or
hard set. An independent continuous integrator evaluated the same catalog.
[Protocol and fixture assumptions](../../research/protocols/TYRE_OPTIMAL_CONTROL_R042.md)

| Substeps per lap | Worst time error across all plans | Error in pit break-even loss |
|---:|---:|---:|
| 4 | 37.541 ms | 12.662 ms |
| 16 | 9.103 ms | 1.352 ms |
| 64 | 2.256 ms | 0.195 ms |
| 256 | 0.563 ms | 0.049 ms |

The reference pit break-even loss is **12.382 s** for this fixture.
At a 2 s loss, both the fine mesh and the reference prefer a fresh soft
before lap two. At a 20 s loss, both prefer no stop. Relative to
conserving on every lap without stopping, those decisions save 10.734 s
and 0.352 s in the fixture, respectively. Maximum heat balance error was
4.02 × 10⁻¹¹ J. Wear increased within each stint and reset on replacement.
[Sealed summary](tyre-optimal-control-r042-summary.json)

The fixture uses one effective axle, two fixed effort levels, assumed
compound parameters and a fixed operating clock. The break-even result
applies to that fixture. R042 remains in progress pending validation with
supported compound pace and observed pit loss. R041 remains open. A new
forecast-time signal for individual car pace triggers an R041 follow-up
on the seven persistent failures, the full development cohort and,
following a complete development pass, fresh confirmation.
[R041 persistent failures](compound-v31-report.md#remaining-evidence-gap)

## Reproduce

Run from the repository root with the installed APEX environment.

```powershell
python -m apexsim.cli run-tyre-optimal-control-study --output .cache/r042-control-replay
python -m pytest -q apex_engine/tests/test_tyre_optimal_control.py apex_engine/tests/test_tyre_thermal.py apex_engine/tests/test_tyre_wear.py
```

The command writes the fixture, full trajectories, sealed summary and
hash inventory. Two local runs produced byte-identical trajectory files.
The parent R039 reference run reproduced the published
summary seal from the accepted R037 replay. The 13 parent tests passed
before implementation. All 15 focused tests passed after implementation
on Windows with Python 3.12.12. The research foundation is R1 and the
production kernel is R0.
