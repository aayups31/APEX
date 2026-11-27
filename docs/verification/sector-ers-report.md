# R043 sector energy and R044 shrinking-horizon feedback

Both research gates passed on the six-sector synthetic fixture. The
continuous optimizer matched the best time change of −2.400 s among
96 feasible exhaustive-grid paths. Its replay obeyed sector, battery
and terminal bounds. The infeasible terminal case was rejected.
[Registered protocol](../../research/protocols/SECTOR_ERS_R043_R044.md)

After disturbances to braking and deployment opportunities, the
shrinking-horizon policy finished at the required 1.000 MJ. The
locally limited fixed plan finished at 0.875 MJ. The feedback policy
saved 1.675 s against zero energy use, compared with 1.800 s for a
feasible plan given all disturbances in advance. The first feedback
action was identical with or without later disturbances. The longest
observed solve in the saved run was about 5.4 ms.
[Sealed summary](sector-ers-summary.json)

The input opportunities, efficiency and time effects are synthetic
priors. Real-car energy measurement and season-specific regulations
remain outside these research gates.
[Primary paper](https://doi.org/10.1109/TVT.2023.3237388)

```powershell
python -m apexsim.cli run-sector-ers-study --output .cache/r043-r044-replay
python -m pytest -q apex_engine/tests/test_sector_ers.py apex_engine/tests/test_research_fienia_strategy.py
```
