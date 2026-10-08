# Public-source temporal alignment

P1-06 links one explicitly identified session across verified FastF1, OpenF1 and
Jolpica archives, then reports timing coverage without altering source values.
The output is diagnostic evidence at maturity R0, not a training dataset.

## Run

From the repository root, using previously acquired archives:

```powershell
.venv/Scripts/python.exe -m apexsim.cli align-public-data --fastf1 .cache/fastf1-2024-r12-q-v2 --openf1 .cache/openf1-9554-20260916 --jolpica .cache/jolpica-2024-20260916 --link docs/data/session-links/british-2024-q.json --output .cache/alignment-british-2024-q-new
```

Choose a new output directory outside all source archives. Verification runs before
and after alignment; corrupted inputs or changed archive hashes prevent completion.
This command reads saved files and does not acquire data. Acquisition commands are
documented in the [FastF1](fastf1-archives.md), [OpenF1](openf1-archives.md) and
[Jolpica](jolpica-events.md) guides.

## Session identity and clocks

The link JSON is an explicit mapping assertion with a rationale. Validation checks
season, round, session type, provider IDs, circuit, calendar dates and equal driver
inventories against the frozen archives. It never infers equivalence from similar
names. A coherent but incorrectly authored provider mapping is still possible;
metadata checks do not independently prove every cross-provider identity.

OpenF1 dates must carry an explicit timezone offset. FastF1 native dates are treated
as UTC according to that provider's convention. FastF1 weather `Time` is relative
to the saved `t0_date`; the absolute weather timestamp is reconstructed as their sum.
Timestamps retain nanosecond resolution. Unsupported dates outside 1950–2100 fail.
Missing timestamps stay missing. Actual FastF1 session-start timing and the OpenF1
scheduled start are reported separately; their difference is not fitted or applied
as a clock correction.

## Declared policy

Optional `--policy path.json` overrides fields of `AlignmentPolicy`. Values must be
integer milliseconds from 0 through 86,400,000; unknown keys fail. Defaults were
declared before the acceptance run, with no optimization against its join rates:

| Field | Default (ms) | Use |
|---|---:|---|
| `car_location_ms` | 1,000 | Latest location at or before each car sample |
| `car_weather_ms` | 90,000 | Latest weather at or before each car sample |
| `cross_telemetry_ms` | 10 | Nearest cross-provider car/location diagnostic |
| `cross_weather_ms` | 1,000 | Nearest cross-provider weather diagnostic |
| `telemetry_gap_ms` | 1,000 | Report larger car/location timestamp gaps |
| `weather_gap_ms` | 90,000 | Report larger weather timestamp gaps |

These are PRIOR diagnostic choices, not calibrated physical-error bounds or training
acceptance thresholds. Every join records direction, tolerance, row counts, join
rate, unmatched reasons, future matches, target reuse and signed/absolute timing
statistics. Empty comparisons report null statistics, not zero error.

Within each provider and driver, car-to-location and car-to-weather associations
use backward joins. This prevents future recorded timestamps from being selected.
Actual publication/availability latency is unknown, so this alone does not prove
online information availability. Target reuse is allowed and counted (many car
samples may refer to one weather record). No interpolation or forward filling of
source values occurs.

Cross-provider joins use nearest timestamps for retrospective diagnostics only.
Equal-distance ties prefer the earlier timestamp. Future matches are explicitly
counted; these pairs must not feed causal policies. If a chosen target timestamp
has multiple records, it is ambiguous and remains unmatched; the matcher does not
silently pick one duplicate or fall back to a different timestamp. Source-order
reversals are reported, and output row indices retain original input order.

## Output and lineage

```text
alignment/
  session_link.json
  policy.json
  pairs/*.parquet       # temporal associations and outer-joined driver/lap keys
  report.json           # stream quality, join statistics and source disagreements
  manifest.json         # file hashes/sizes and completion marker, written last
```

Temporal pair indices are zero-based within the original provider stream after
filtering to that driver; weather indices refer to the whole weather table.
`left_row` is always present, including for missing/unmatched timestamps.
`right_row`, `right_utc` and timing delta are null for unmatched rows. Right-minus-left
deltas are in milliseconds. Raw values remain addressable in the input archives.

All car/location streams and both weather streams report missing timestamps,
duplicate timestamp rows, source-order reversals and every gap above the declared
threshold. A gap is an observation about coverage, not proof of an upstream fault.
Lap comparison uses an outer join on driver/lap keys, rejects duplicate keys and
retains missing starts/durations. Race-control comparison uses exact UTC timestamp,
category and message with duplicate multiplicity preserved; unmatched messages
remain visible. It does not produce a merged flag state or reconcile message meaning.

The report records source archive hashes, code hashes, environment, policy and link.
The final manifest covers every output file except itself and contains its own
content hash. Failed runs can leave partial diagnostic files but no completion
manifest. Outputs are immutable by convention and overwrite is refused; hashes
support integrity checks, not signatures or tamper-proof storage.

Provider-supplied values retain their source truth labels. Normalized timestamps,
associations, counts and deltas are RECONSTRUCTED diagnostics. No source is promoted
to calibrated ground truth. `report_complete: true` means processing completed;
`training_ready: false` remains explicit. Timing agreement does not establish
semantic agreement, independent measurements or simulator realism.

See the [acceptance report](../verification/temporal-alignment-report.md) for the
frozen British 2024 qualifying case. Other sessions can use their own verified
archives and explicit link files; this single-session evidence does not establish
multi-circuit coverage. P1-07 handles canonical observed fields and placeholder
removal, followed by broader telemetry acquisition and held-out evaluation.
