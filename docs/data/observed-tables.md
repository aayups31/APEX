# Observed public fields

P1-07 maps verified source archives into the existing five public evidence tables.
Weather, tyre compound and pit timestamps come from supported source fields; missing
or incompatible observations stay null with UNKNOWN truth labels. These bundles
support inspection and later model preparation. Maturity remains R0.

## Commands

From the repository root, with the archives used by the alignment milestone:

```powershell
.venv/Scripts/python.exe -m apexsim.cli build-observed-tables --fastf1 .cache/fastf1-2024-r12-q-v2 --openf1 .cache/openf1-9554-20260916 --jolpica .cache/jolpica-2024-20260916 --link docs/data/session-links/british-2024-q.json --output .cache/observed-british-2024-q-new
.venv/Scripts/python.exe -m apexsim.cli validate-public-data .cache/observed-british-2024-q-new/fastf1
.venv/Scripts/python.exe -m apexsim.cli validate-public-data .cache/observed-british-2024-q-new/openf1
.venv/Scripts/python.exe -m apexsim.cli verify-observed-tables .cache/observed-british-2024-q-new
```

Outputs must be new directories outside source archives. Use the existing
`download-fastf1`, `download-openf1` and `download-jolpica` commands for acquisition,
then provide a reviewed explicit session link. Conversion verifies all three frozen
archives before and after processing and makes no HTTP requests.

The retired `ingest-fastf1` and `ingest-openf1` CSV commands return migration
instructions before downloading or writing anything. Their saved dense CSVs are
also rejected by the public training ingestion path, even with an old valid source
manifest. [ADR 0003](../architecture/adr-0003-observed-public-fields.md) records this
intentional API change. The synthetic CSV pipeline remains runnable. A validated
feature builder with missingness handling is still required for public-data training.

## Mapping contract

Each provider gets its own bundle. Both session IDs share the same event ID from
the checked link, so later split manifests can group them by event. No source field
is copied across providers. Every canonical data field carries a truth label under
[public-tables-v1](public-tables.md). MEASURED means supplied by a declared provider;
native provider values may themselves include reconstructions. Unit conversions,
row associations and generated IDs are RECONSTRUCTED. No field is IMPUTED.

| Evidence | FastF1 mapping | OpenF1 mapping |
|---|---|---|
| Weather | `weather_data` native fields | `weather` native fields |
| Pressure | hPa to Pa, multiplying by 100 | mbar to Pa, multiplying by 100 |
| Rainfall | Supplied boolean | Supplied boolean or numeric 0/1, converted to boolean |
| Lap compound | Native lap `Compound` | Compound from one uniquely covering source stint |
| Lap tyre age | Native `TyreLife`, as reported | UNKNOWN; no age formula is guessed |
| Pit entry/exit | Native `PitInTime` / `PitOutTime` | UNKNOWN; generic pit date/durations do not establish both boundaries |
| Stint bounds | First/last observed lap in the native driver/stint group | Native bounds only when compatible with the canonical inclusive range contract |
| Stint-start tyre age | UNKNOWN; per-lap tyre life is not substituted | Native `tyre_age_at_start` for accepted stint rows |
| Lap accuracy/status | Native `IsAccurate` / `TrackStatus` | UNKNOWN where no equivalent field is supplied |
| Race control | Original messages and optional fields | Original messages and optional fields |

Absent temperatures, winds and rainfall never become fixed values. Unsupported
compound taxonomies stay unknown and receive an issue entry; original strings remain
in the native archive. Missing pit timestamps never become a false pit-occupancy
flag. Grip and safety-car feature constants are not generated.

Native race-control sector indices belong to a different namespace from the three
lap timing sectors allowed by the canonical table. Present source sector values
are retained through the archive/lineage and receive an issue entry; canonical
`sector` stays UNKNOWN. Original messages such as `YELLOW IN TRACK SECTOR 10`
remain verbatim. Values are never clipped into 1–3 or assumed equivalent merely
because their numbers happen to fall within that range.

FastF1 lap and pit times are converted from the native data clock to seconds relative
to its recorded session start. Its weather timestamps use `t0_date + Time`. OpenF1
lap starts use its reported scheduled start as the time origin. Those origins are
different and retained in the session records and report; no clock adjustment is
fitted. Before-start values that cannot fit the nonnegative v1 relative-time contract
stay unknown with a reason. UTC timestamps must represent exact microseconds;
finer precision fails instead of being rounded silently. No weather is interpolated
or assigned to telemetry in this milestone.

## Stint ambiguity

The canonical stint contract uses inclusive lap bounds and forbids overlapping
stints for the same driver. Some native OpenF1 rows share boundary laps. Both rows
of an overlap are quarantined from the canonical stint table. The report identifies
their original indices; it does not decide which tyre was on a disputed lap.

A lap compound can still be associated with a single uniquely covering bounded
native stint. A lap with multiple candidates has unknown compound, even if the
candidate strings happen to agree. Its stint ID is unknown if the selected row was
quarantined. Unbounded or reversed ranges are quarantined; missing observations
do not become inferred bounds. This conservative conversion can produce an empty
canonical stint table while all native stint rows remain preserved for investigation.
An empty table is explicit incomplete coverage, not evidence of no stints.

FastF1 stint bounds describe the observed lap extent in that native group. They do
not prove coverage before its first or after its last recorded lap. A conflicting
compound inside one group fails conversion. Lap-level missing compounds remain
unknown even when another lap in the group reports a compound.

## Artifacts and lineage

```text
observed/
  session_link.json
  fastf1.source.json           # derived provenance with preserved request metadata
  openf1.source.json
  fastf1/                     # sessions, laps, stints, weather, race_control + manifest
  openf1/
  fastf1.lineage.json          # native input row references in canonical output order
  openf1.lineage.json
  report.json                 # missingness, issues, coverage, limits, code/source hashes
  manifest.json               # run completion marker, all output file hashes/sizes
```

Lineage row indices are zero-based in the native table's saved order. Derived
FastF1 stints reference all contributing lap rows. OpenF1 lap lineage includes every
candidate stint row. Unmapped pit records are counted and remain in the archive.
Original messages remain verbatim; source-order IDs preserve same-time messages.

Source snapshots carry the original acquisition requests/times and reference the
verified archive manifest and mapping input files. The derived manifest's access
time is conversion time. Bundle hashes include these provenance snapshots, so two
conversions can have different bundle hashes while producing identical values.
Dataset readers verify schema, truth labels, file hashes and cross-table references;
relocated bundles can be read without the original native cache. The enclosing run
manifest also covers lineage and the conversion report. A failed conversion can
leave diagnostic files but has no enclosing completion manifest.

`verify-observed-tables` checks the exact run file inventory, completion hashes,
provider datasets, recorded missingness and native lineage table/index bounds.
It supports relocated complete runs without the source caches. These checks establish
recorded integrity and consistency, not authenticity of the original observations.

`report_complete` means conversion finished. `training_ready` stays false: schema
validation does not establish complete source coverage, physical accuracy, online
information availability or predictive generalization. The recorded lap-start
disagreements still require investigation before canonical telemetry is assembled.

Sources inspected for the mapping: [OpenF1 field documentation](https://openf1.org/docs/)
and the installed FastF1 3.8.3 `_api.py`/`core.py` field documentation. See the
[acceptance report](../verification/observed-public-fields-report.md) for the real run.
