# R038 independent-event confirmation

The original detector exceeded the nominal fallback cap on all four 2024 Monza
conditions. The second candidate estimates its cutoff from three continuous
development trajectories. The frozen cutoff is 2.27745, compared with 1.26874
for the first candidate. The empirical feature widths, ten-command release rule,
5% fallback cap, hard bounds, and injected raw feature-shift amplitude stay as
preregistered. The new calibration was pushed in `8e844df` before confirmation.
[First campaign](recovery-support-report.md) · [Second protocol](../../research/protocols/SUPPORT_FALLBACK_V2.md) · [Calibration seal](support-v2-calibration.json)

The independent event is 2025 Monza qualifying. OpenF1 session 9908 supplies
two native starting speeds each for drivers 4 and 44, sampled 0.034–0.292 seconds
after lap start. All subsequent trajectories use the frozen Monza map and
simulated vehicle. This evaluates the revised supervisor on new initial
conditions at a known circuit.
[Official qualifying results](https://www.formula1.com/en/results/2025/races/1268/italy/qualifying)

The 52-case campaign passed every preregistered gate. All four nominal guarded
runs spent 0% of commands in fallback. All guarded fault cases rejected the
injected actions and returned control to the learned driver. All 12 hard cases
abstained before applying a command. The separate physics audit checked 96
intervals around 48 controller handovers. The bound inspection checked 132,582
saved actions and detected all 16 out-of-envelope feature-axis probes. An
in-envelope combined shift remains a blind spot for the axis-aligned detector.
[Primary summary](support-v2-primary-summary.json) · [All cases](support-v2-primary-results.json) · [Boundary inspection](support-v2-boundaries.json)

Full regeneration is in progress. The implementation passed 758 local tests
and 758 tests in each GitHub CI job.
[Implementation CI](https://github.com/aayups31/APEX/actions/runs/41701813990)

```powershell
apexsim download-openf1 --session-key 9908 --output .cache/monza-2025-openf1
apexsim run-support-confirmation --detector .cache/r038-detector-20261101 --frozen docs/verification/support-v2-calibration.json --archive .cache/monza-2025-openf1 --output .cache/r038-confirmation-fresh
apexsim run-support-confirmation --detector .cache/r038-detector-20261101 --frozen docs/verification/support-v2-calibration.json --archive .cache/monza-2025-openf1 --output .cache/r038-confirmation-fresh --verify --receipt .cache/r038-confirmation-fresh-replay.json
```
