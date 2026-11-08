# R041 TracingInsights archive investigation

The archive is a viable free source for a new processed-telemetry experiment.
It resolves file availability for the 301 R041 comparisons currently missing
driving observations. It requires an explicit data contract and timing
validation before model evaluation.

## Verified coverage

Pinned repository TracingInsights/2025 at
dfb3ea3f50b69857fe8e40cabe5e899743c59f6a. The inventory checks all 19 already
opened 2025 race folders. All 2,561 distinct required known-lap telemetry paths
exist. These cover the three completed input windows for every one of the
301 supported comparisons. Four opened races have no eligible comparisons.
File existence does not establish channel quality across those files.

The guard runs before any event payload access. Only opened event driver
metadata was downloaded for the inventory. Reserved or unopened race payloads
were not acquired. Each metadata response is cached with its original body,
URL and digest.

The Japanese race pilot confirms telemetry arrays for speed, throttle, brake,
DRS and lap-relative time. Companion files expose driver numbers, compounds,
stints, tyre lives, lap start dates and session identity. This supports a
driver/lap association to APEX's existing sealed targets.

## Native comparison

Pinned TracingInsights/2024 at d1543a71370d9b617b627319f8ad80b2f85dfd5e.
The pilot compares driver 11's Bahrain race laps 14, 38 and 23, which belong
to the already known windows of R041 comparison 267.

| Lap | Native samples | Export samples | Mean speed difference |
|---|---:|---:|---:|
| 14 | 359 | 733 | +0.0666 m/s |
| 38 | 351 | 719 | -0.2997 m/s |
| 23 | 350 | 732 | -0.3940 m/s |

Maximum absolute mean throttle difference is 0.00642 of full scale. Maximum
absolute mean brake difference is 0.00821. This is a three-lap diagnostic,
without an equivalence tolerance or a claim about the full dataset. Values
are time-weighted using the registered v19 arithmetic for comparison only.

## Processing differences

The generation code calls FastF1 get_telemetry(), merging and interpolating
car and position observations. The exported files omit native Date,
SessionTime and Source columns. Their time arrays are lap relative, include
constructed endpoints, and need association through lap start metadata.

The sampled exports encode DRS as binary 0/1. APEX's native DRS mapping
interprets the native code 1 as closed. A dedicated adapter must map the
exported binary representation correctly. Simply passing these values through
the current native decoder would lose DRS-open observations.

Interpolation can change speed and control averages and can use neighboring
observations at lap boundaries. Original source timing cannot be recovered
exactly from these exports. Future-boundary influence needs an explicit
analysis before using the latest completed lap for a causal forecast.
Derived accelerations also include gradients, smoothing and outlier treatment.

The README's fuel correction assumes 100 kg initially and proportional
depletion over the race. APEX's frozen labels use a different fuel prior.
Keep the existing target definitions when studying these additional inputs.

The repository advertises an Apache-2.0 license. Source attribution and
processing provenance should accompany acquisition.

## Recommended implementation

1. Freeze a new processed-observation protocol with source representation,
   clock association, DRS conversion, missingness and boundary influence
   requirements. V19's native-sample acceptance cannot certify this export.
2. Acquire only required opened-event input laps at pinned commits and
   verify event, driver, lap, compound and clock agreement.
3. Expand the native comparison beyond three laps, including all nine
   archived races and each control regime. Measure channel and timing error.
4. Check companion 2023/2024 archive coverage before choosing whether to use
   one consistent exported representation across the entire training cohort.
5. Evaluate the registered model on all original cases, keeping every race
   gate and a matched input ablation. Only a development pass permits a
   separate prospective confirmation.

No prediction model was fitted in this investigation. R041 remains open.

## Reproduction and evidence

Run from the repository root with fresh output paths. The network inventory
cache allows verified offline repetition of the same requests.

```text
python research/scripts/inspect_tracing_archive.py --cache .cache/r041-tracing-inventory --output <fresh-inventory.json>
```

[Coverage receipt](compound-tracing-inventory.json),
[three-lap native comparison](compound-tracing-native-pilot.json).

Sources inspected include the pinned
[2025 repository](https://github.com/TracingInsights/2025/tree/dfb3ea3f50b69857fe8e40cabe5e899743c59f6a),
[export code](https://github.com/TracingInsights/2025/blob/dfb3ea3f50b69857fe8e40cabe5e899743c59f6a/telR_new.py),
[2024 repository](https://github.com/TracingInsights/2024/tree/d1543a71370d9b617b627319f8ad80b2f85dfd5e).
