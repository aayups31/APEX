# Pipeline stages

Each stage has path-based inputs/outputs and can reuse an existing immutable artifact, supporting retries and local/Airflow parity.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?

## Real-data handoff

`ingest_stage` has two valid entry paths:

1. Generate offline synthetic evidence directly into the run directory.
2. Copy a previously validated canonical FastF1/OpenF1 CSV from `config.data.canonical_input_path`.

The copy is not redundant. It freezes the exact training evidence inside the run's immutable artifact boundary. From that point onward, no downstream function branches on the external source.
