# R041 outlap input coverage

Across the seven recurring failure races, 117 of 131 cases have an
officially timed outlap and at least three clean laps from other drivers
on the same race lap. Each peer finished within 120 seconds of the
subject's outlap and before or at the subject's original forecast cutoff.
The proxy is the subject's raw outlap duration minus the median duration
of those peers. Counts are comparison windows, which can share outlaps.

| Event | Cases | Outlap pace proxy | Exact pit-exit clock | Both |
|---|---:|---:|---:|---:|
| 9850 | 13 | 13 | 0 | 0 |
| 9877 | 33 | 33 | 0 | 0 |
| 9912 | 12 | 12 | 0 | 0 |
| 9928 | 36 | 36 | 0 | 0 |
| 9998 | 10 | 10 | 0 | 0 |
| F1_2023_R15 | 14 | 0 | 14 | 0 |
| F1_2024_R16 | 13 | 13 | 13 | 13 |

FastF1 supplies a pit-out timestamp that can be reconciled to its lap
clock even when the official duration is absent. This occurred for all
14 Singapore 2023 cases. The OpenF1 lap archives identify the outlap.
The OpenF1 pit schema does not specify that its event date is the exact
pit-exit timestamp. This audit uses the verified local archives.
[OpenF1 schema](https://openf1.org/docs/#pit) ·
[Case-level evidence](compound-outlap-support.json)

Run one race-held-out R041 forecast experiment with relative outlap pace
and explicit missing support. Use the seven recurring failures as
diagnostics and preserve the full development panel for qualification.
Treat the joint exact-clock feature as a separate coverage question.
The raw outlap comparison includes pit transit, traffic and driving
effects. The audit measured coverage only. Predictive gain and
real-time availability of final archive quality flags remain unverified.

```powershell
python research/scripts/audit_compound_outlap_support.py --output .cache/r041-outlap-support-replay.json
```
